"""Codex app-server backend.

Codex decides the next ReAct action. Python owns every retrieval tool,
cache write, archive write, and trace record.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from research_agent.tool_registry import (
    ToolRegistry,
    ToolValidationError,
    build_default_registry,
)
from research_agent.types import CritiqueResult, ResearchResult, ToolCallRecord

log = logging.getLogger(__name__)


GROUNDING_RULES = """\
Answer research questions by calling the available tools, reading sources, and
then writing a grounded synthesis.

Grounding rules:
1. Citations must be real and observed in this session's tool results.
2. Prefer primary sources: papers, official docs, and official repos.
3. For sparse or negative findings, try several distinct query phrasings and
   mention the searches tried.
4. Unknown is acceptable. Never fabricate rows, years, authors, URLs, repos, or
   arXiv IDs.
5. Inline citations use [arXiv:id], [owner/repo], or source URLs.
"""


ACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["call_tool", "finish"]},
        "tool": {"type": "string"},
        "args": {
            "type": "string",
            "description": "A JSON object encoded as a string. Use '{}' when finishing.",
        },
        "synthesis": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["action", "tool", "args", "synthesis", "sources"],
    "additionalProperties": False,
}


QUERY_EXPANSION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["queries"],
    "additionalProperties": False,
}


RERANK_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "scores": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["scores"],
    "additionalProperties": False,
}


CRITIQUE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "coverage_gaps": {"type": "array", "items": {"type": "string"}},
        "likely_errors": {"type": "array", "items": {"type": "string"}},
        "grounding_score": {"type": "integer"},
        "suggested_prompt_tweak": {"type": "string"},
        "overall_verdict": {"type": "string"},
    },
    "required": [
        "coverage_gaps",
        "likely_errors",
        "grounding_score",
        "suggested_prompt_tweak",
        "overall_verdict",
    ],
    "additionalProperties": False,
}


@dataclass(frozen=True, slots=True)
class CodexConfig:
    codex_bin: str
    model: str | None
    effort: str
    timeout_sec: float
    rpc_log: bool
    stdio_limit: int
    tool_result_max_chars: int
    context_max_chars: int

    @classmethod
    def from_env(
        cls,
        *,
        codex_model: str | None = None,
        codex_effort: str | None = None,
        codex_timeout: float | None = None,
    ) -> "CodexConfig":
        return cls(
            codex_bin=os.environ.get("CODEX_BIN", "codex"),
            model=codex_model or os.environ.get("CODEX_MODEL") or None,
            effort=codex_effort or os.environ.get("CODEX_EFFORT", "low"),
            timeout_sec=float(
                codex_timeout or os.environ.get("CODEX_TIMEOUT_SEC", "600")
            ),
            rpc_log=os.environ.get("CODEX_RPC_LOG") in ("1", "true", "yes"),
            stdio_limit=int(
                os.environ.get(
                    "CODEX_STDIO_LIMIT",
                    os.environ.get("CODEX_CONTROL_STDIO_LIMIT", str(16 * 1024 * 1024)),
                )
            ),
            tool_result_max_chars=int(os.environ.get("RA_TOOL_RESULT_MAX_CHARS", "12000")),
            context_max_chars=int(os.environ.get("RA_CONTEXT_MAX_CHARS", "48000")),
        )


@dataclass(slots=True)
class CodexAction:
    action: str
    tool: str
    args: dict[str, Any]
    synthesis: str
    sources: list[str]


class CodexUnavailable(RuntimeError):
    """Raised when the optional Codex backend cannot start."""


class CodexResearchRunner:
    backend_name = "codex"

    def __init__(
        self,
        *,
        config: CodexConfig | None = None,
        session: Any | None = None,
        cwd: Path | str | None = None,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.config = config or CodexConfig.from_env()
        self._session = session
        self.cwd = Path(cwd or os.getcwd())
        self.registry = registry or build_default_registry(
            expanded_search_fn=self._make_expanded_search_tool()
        )

    async def arun(self, question: str, *, current_date: str) -> ResearchResult:
        tool_calls: list[ToolCallRecord] = []
        backend_meta: dict[str, Any] = {"model": self.config.model, "effort": self.config.effort}

        async with self._session_scope() as session:
            thread = await self._start_thread(session)
            backend_meta["thread_id"] = getattr(thread, "thread_id", None)
            observations: list[dict[str, Any]] = []
            try:
                for step in range(int(os.environ.get("MAX_ITERS", "28"))):
                    prompt = self._render_action_prompt(
                        question=question,
                        current_date=current_date,
                        observations=observations,
                        step=step + 1,
                    )
                    turn = await thread.run_turn(
                        prompt,
                        cwd=str(self.cwd),
                        model=self.config.model,
                        effort=self.config.effort,
                        approval_policy="never",
                        output_schema=ACTION_SCHEMA,
                        timeout=self.config.timeout_sec,
                    )
                    action = parse_codex_action(turn.final_text)
                    backend_meta.setdefault("turn_ids", []).append(getattr(turn, "turn_id", None))

                    if action.action == "finish":
                        return ResearchResult(
                            synthesis=action.synthesis.strip(),
                            sources=_dedup_sources(action.sources),
                            backend=self.backend_name,
                            tool_calls=tool_calls,
                            backend_meta=backend_meta,
                        )

                    record, observation = await self._execute_action(action)
                    tool_calls.append(record)
                    observations.append(observation)
            finally:
                with contextlib.suppress(Exception):
                    await thread.archive()

        raise RuntimeError("Codex backend exhausted max iterations without finishing.")

    async def decompose(self, question: str) -> list[str]:
        schema = {
            "type": "object",
            "properties": {"sub_questions": {"type": "array", "items": {"type": "string"}}},
            "required": ["sub_questions"],
            "additionalProperties": False,
        }
        prompt = (
            "Break this broad research question into 3-5 independent, concrete, "
            "searchable sub-questions. Return JSON only.\n\n"
            f"Question: {question}"
        )
        async with self._session_scope() as session:
            thread = await self._start_thread(session)
            try:
                obj = await self._structured_turn(thread, prompt, schema)
            finally:
                with contextlib.suppress(Exception):
                    await thread.archive()
        subs = [str(q).strip() for q in obj.get("sub_questions", []) if str(q).strip()]
        return subs[:5] if len(subs) >= 2 else [question]

    async def merge(
        self,
        *,
        original_question: str,
        sub_questions: list[str],
        sub_syntheses: list[str],
        all_sources: list[str],
    ) -> ResearchResult:
        schema = {
            "type": "object",
            "properties": {
                "synthesis": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["synthesis", "sources"],
            "additionalProperties": False,
        }
        prompt = (
            f"{GROUNDING_RULES}\n\n"
            "Merge the sub-syntheses into one cohesive answer. Deduplicate "
            "overlap, preserve citations, and note contradictions.\n\n"
            f"Original question:\n{original_question}\n\n"
            f"Sub-questions:\n{json.dumps(sub_questions, indent=2)}\n\n"
            f"Sub-syntheses:\n{json.dumps(sub_syntheses, indent=2)}\n\n"
            f"All sources:\n{json.dumps(all_sources, indent=2)}"
        )
        async with self._session_scope() as session:
            thread = await self._start_thread(session)
            try:
                obj = await self._structured_turn(thread, prompt, schema)
            finally:
                with contextlib.suppress(Exception):
                    await thread.archive()
        return ResearchResult(
            synthesis=str(obj.get("synthesis", "")).strip(),
            sources=_dedup_sources([str(s) for s in obj.get("sources", [])]),
            backend=self.backend_name,
        )

    def _make_expanded_search_tool(self) -> Callable[..., Any]:
        async def expanded_search(question: str, top_k: int = 10) -> str:
            return await self._codex_expanded_search(question, top_k=top_k)

        expanded_search.__name__ = "expanded_search"
        expanded_search.__doc__ = (
            "LM-expanded, reranked web search. Use this when a query needs "
            "synonym coverage, adjacent terminology, or broader recall than web_search."
        )
        return expanded_search

    async def _codex_expanded_search(self, question: str, top_k: int = 10) -> str:
        from research_agent.tools import _dedupe_by_url, _fmt_block, _parse_result_blocks, web_search

        queries = [question]
        try:
            async with self._session_scope() as session:
                thread = await self._start_thread(session)
                try:
                    obj = await self._structured_turn(
                        thread,
                        (
                            "Expand this research question into 4-6 short, distinct "
                            "web search queries. Prefer 2-6 words each. Return JSON only.\n\n"
                            f"Question: {question}"
                        ),
                        QUERY_EXPANSION_SCHEMA,
                    )
                finally:
                    with contextlib.suppress(Exception):
                        await thread.archive()
            expanded = [str(q).strip() for q in obj.get("queries", []) if str(q).strip()]
            queries = list(dict.fromkeys(expanded))[:6] or queries
        except Exception as exc:
            log.debug("Codex query expansion failed: %s", exc)

        pool: list[dict[str, Any]] = []
        contributors: dict[str, int] = {}
        for query in queries:
            try:
                raw = await asyncio.to_thread(web_search, query)
            except Exception as exc:
                log.debug("expanded_search query failed %r: %s", query, exc)
                continue
            parsed = _parse_result_blocks(raw)
            contributors[query] = len(parsed)
            pool.extend(parsed)

        pool = _dedupe_by_url(pool)
        if not pool:
            return f"expanded_search: no results across {len(queries)} queries.\nTried: {queries}"

        shortlist = pool[:24]
        scores = [5] * len(shortlist)
        try:
            async with self._session_scope() as session:
                thread = await self._start_thread(session)
                try:
                    obj = await self._structured_turn(
                        thread,
                        (
                            "Score each candidate's relevance to the research question "
                            "on a strict 0-10 integer scale. Return one score per "
                            "candidate in the same order.\n\n"
                            f"Question: {question}\n\n"
                            f"Candidates:\n{json.dumps([_fmt_block(b) for b in shortlist], indent=2)}"
                        ),
                        RERANK_SCHEMA,
                    )
                finally:
                    with contextlib.suppress(Exception):
                        await thread.archive()
            raw_scores = obj.get("scores", [])
            scores = [int(s) for s in raw_scores[: len(shortlist)]]
            scores += [0] * (len(shortlist) - len(scores))
        except Exception as exc:
            log.debug("Codex rerank failed: %s", exc)

        scored = sorted(zip(scores, shortlist), key=lambda item: item[0], reverse=True)
        top = scored[: max(1, int(top_k))]
        header = (
            f"[expanded_search · {len(queries)} queries → {len(pool)} merged "
            f"→ top {len(top)} after rerank]\n"
            f"queries tried: {queries}\n"
            f"contributors: {contributors}\n"
        )
        body = "\n\n".join(f"[rerank={score}] {_fmt_block(block)}" for score, block in top)
        return header + "\n" + body

    async def _execute_action(self, action: CodexAction) -> tuple[ToolCallRecord, dict[str, Any]]:
        try:
            result_text, record = await self.registry.acall(action.tool, action.args)
        except ToolValidationError as exc:
            record = ToolCallRecord(
                tool=action.tool,
                args=action.args,
                ok=False,
                error=str(exc),
            )
            result_text = ""

        observation = {
            "tool": record.tool,
            "args": record.args,
            "ok": record.ok,
            "elapsed_ms": record.elapsed_ms,
            "result": _clamp(result_text, self.config.tool_result_max_chars),
            "error": record.error,
        }
        return record, observation

    def _render_action_prompt(
        self,
        *,
        question: str,
        current_date: str,
        observations: list[dict[str, Any]],
        step: int,
    ) -> str:
        observation_text = json.dumps(observations, indent=2, ensure_ascii=False)
        observation_text = _tail_clamp(observation_text, self.config.context_max_chars)
        return (
            f"{GROUNDING_RULES}\n\n"
            f"Current date: {current_date}\n"
            f"Question: {question}\n"
            f"Step: {step}\n\n"
            "Available tools:\n"
            f"{self.registry.render_for_prompt()}\n\n"
            "Observations so far, in order:\n"
            f"{observation_text}\n\n"
            "Choose exactly one next action.\n"
            "- If more evidence is needed, set action='call_tool', tool to one "
            "available tool name, args to a JSON-object string, synthesis='', sources=[].\n"
            "- If enough evidence is available, set action='finish', tool='', args='{}', "
            "synthesis to the final cited answer, and sources to every cited source."
        )

    async def _structured_turn(self, thread: Any, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        turn = await thread.run_turn(
            prompt,
            cwd=str(self.cwd),
            model=self.config.model,
            effort=self.config.effort,
            approval_policy="never",
            output_schema=schema,
            timeout=self.config.timeout_sec,
        )
        return _loads_object(turn.final_text)

    async def _start_thread(self, session: Any) -> Any:
        return await session.start_thread(
            cwd=str(self.cwd),
            ephemeral=True,
            sandbox="read-only",
            approval_policy="never",
            model=self.config.model,
            developer_instructions=GROUNDING_RULES,
        )

    @contextlib.asynccontextmanager
    async def _session_scope(self) -> AsyncIterator[Any]:
        if self._session is not None:
            yield self._session
            return
        session = new_codex_session(self.config)
        async with session:
            yield session


async def run_codex_critique(
    question: str,
    synthesis: str,
    sources: list[str],
    *,
    config: CodexConfig | None = None,
    cwd: Path | str | None = None,
) -> CritiqueResult:
    config = config or CodexConfig.from_env()
    runner = CodexResearchRunner(config=config, cwd=cwd)
    prompt = (
        "Review this research synthesis against the rubric. Be specific. "
        "Do not invent problems if the output is well grounded.\n\n"
        f"Current date: {datetime.now().date().isoformat()}\n"
        f"Question:\n{question}\n\n"
        f"Synthesis:\n{synthesis}\n\n"
        f"Sources:\n{json.dumps(sources, indent=2)}"
    )
    async with runner._session_scope() as session:
        thread = await runner._start_thread(session)
        try:
            obj = await runner._structured_turn(thread, prompt, CRITIQUE_SCHEMA)
        finally:
            with contextlib.suppress(Exception):
                await thread.archive()
    return CritiqueResult(
        coverage_gaps=[str(x) for x in obj.get("coverage_gaps", [])],
        likely_errors=[str(x) for x in obj.get("likely_errors", [])],
        grounding_score=max(1, min(5, int(obj.get("grounding_score", 0)))),
        suggested_prompt_tweak=str(obj.get("suggested_prompt_tweak", "")),
        overall_verdict=str(obj.get("overall_verdict", "")),
    )


async def arun_codex_parallel(
    question: str,
    *,
    max_workers: int | None = None,
    config: CodexConfig | None = None,
    cwd: Path | str | None = None,
) -> ResearchResult:
    from research_agent.parallel import arun_parallel

    config = config or CodexConfig.from_env()
    session = new_codex_session(config)
    async with session:
        planner = CodexResearchRunner(config=config, session=session, cwd=cwd)

        def runner_factory() -> CodexResearchRunner:
            return CodexResearchRunner(config=config, session=session, cwd=cwd)

        return await arun_parallel(
            question,
            runner_factory=runner_factory,
            max_workers=max_workers,
            decompose_fn=planner.decompose,
            merge_fn=planner.merge,
        )


async def codex_smoke_check(config: CodexConfig | None = None) -> tuple[bool, str]:
    config = config or CodexConfig.from_env()
    if shutil.which(config.codex_bin) is None:
        return False, f"{config.codex_bin!r} not found on PATH"
    try:
        new_codex_session(config)
    except Exception as exc:
        return False, str(exc)

    smoke_config = CodexConfig(
        codex_bin=config.codex_bin,
        model=config.model,
        effort=config.effort,
        timeout_sec=min(config.timeout_sec, 120),
        rpc_log=False,
        stdio_limit=config.stdio_limit,
        tool_result_max_chars=config.tool_result_max_chars,
        context_max_chars=config.context_max_chars,
    )
    schema = {
        "type": "object",
        "properties": {"ok": {"type": "boolean"}},
        "required": ["ok"],
        "additionalProperties": False,
    }
    try:
        runner = CodexResearchRunner(config=smoke_config, cwd=tempfile.gettempdir())
        async with runner._session_scope() as session:
            thread = await runner._start_thread(session)
            try:
                obj = await runner._structured_turn(
                    thread,
                    "Return JSON with ok=true. No prose.",
                    schema,
                )
            finally:
                with contextlib.suppress(Exception):
                    await thread.archive()
        if obj.get("ok") is True:
            return True, "codex app-server structured-output smoke passed"
        return False, f"unexpected smoke response: {obj!r}"
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def new_codex_session(config: CodexConfig) -> Any:
    try:
        from codex_control.session import CodexSession
        from codex_control.transport import StdioTransport
    except Exception as exc:
        raise CodexUnavailable(
            "Codex backend requires the optional codex extra: "
            "pip install 'research-swarm[codex]'. "
            f"Import failed with {type(exc).__name__}: {exc}"
        ) from exc

    transport = StdioTransport(
        config.codex_bin,
        stream_limit=config.stdio_limit,
        stderr_cb=(lambda line: print(f"[codex] {line}", file=sys.stderr))
        if os.environ.get("RA_VERBOSE")
        else None,
    )
    rpc_logger = _rpc_logger_factory(_rpc_log_path()) if config.rpc_log else None
    return CodexSession(
        transport,
        client_name="research-swarm",
        client_title="research-swarm",
        request_timeout=config.timeout_sec,
        rpc_logger=rpc_logger,
    )


def parse_codex_action(text: str) -> CodexAction:
    obj = _loads_object(text)
    missing = [key for key in ACTION_SCHEMA["required"] if key not in obj]
    if missing:
        raise ValueError(f"Codex action missing required fields: {', '.join(missing)}")
    args = obj.get("args")
    if isinstance(args, str):
        args = json.loads(args or "{}")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ValueError("Codex action args must decode to a JSON object.")
    sources = obj.get("sources")
    if not isinstance(sources, list):
        raise ValueError("Codex action sources must be a list.")
    action = str(obj["action"])
    if action not in ("call_tool", "finish"):
        raise ValueError(f"Unknown Codex action: {action}")
    tool = str(obj.get("tool") or "")
    if action == "call_tool" and not tool:
        raise ValueError("Codex call_tool action requires a tool name.")
    return CodexAction(
        action=action,
        tool=tool,
        args=args,
        synthesis=str(obj.get("synthesis") or ""),
        sources=[str(source) for source in sources],
    )


def _loads_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    candidates = [text]
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fenced:
        candidates.append(fenced.group(1))
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(text[start : end + 1])

    last_error: Exception | None = None
    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
        except Exception as exc:
            last_error = exc
        else:
            if isinstance(obj, dict):
                return obj
            last_error = ValueError("JSON value is not an object.")
            continue

        for match in re.finditer(r"\{", candidate):
            try:
                obj, _ = decoder.raw_decode(candidate[match.start() :])
            except Exception as exc:
                last_error = exc
                continue
            if isinstance(obj, dict):
                return obj
            last_error = ValueError("JSON value is not an object.")
    raise ValueError(f"Could not parse Codex JSON response: {last_error}")


def _dedup_sources(sources: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for source in sources:
        if source and source not in seen:
            seen.add(source)
            result.append(source)
    return result


def _clamp(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _tail_clamp(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return "[older observations trimmed]\n" + text[-limit:]


def _rpc_log_path() -> Path:
    path = Path(os.environ.get("RA_TRACE_DIR", "traces"))
    path.mkdir(parents=True, exist_ok=True)
    return path / f"codex-rpc-{datetime.now():%Y%m%d-%H%M%S}.jsonl"


def _rpc_logger_factory(path: Path) -> Callable[[str, dict[str, Any]], None]:
    fp = path.open("a", buffering=1, encoding="utf-8")

    def emit(direction: str, frame: dict[str, Any]) -> None:
        fp.write(json.dumps({"dir": direction, **frame}, default=str) + "\n")

    emit.close = fp.close  # type: ignore[attr-defined]
    return emit
