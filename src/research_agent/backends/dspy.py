"""DSPy backend wrapper.

The public DSPy compatibility surface remains in :mod:`research_agent.agent`.
This module only adapts it to the backend-neutral runner interface.
"""

from __future__ import annotations

import asyncio
import re

from research_agent.agent import build_agent, configure_lm
from research_agent.types import ResearchResult, ToolCallRecord


# DSPy's ReAct.forward returns a Prediction whose `.trajectory` is a flat
# dict keyed by f"thought_{i}", f"tool_name_{i}", f"tool_args_{i}",
# f"observation_{i}" (see dspy/predict/react.py). Reconstruct
# ToolCallRecords so the trace JSON has a structured per-tool-call history
# instead of an always-empty list. Without this every DSPy run looks like
# the model answered from memory: this is the "violet trace" bug — runs
# would record sources but tool_calls=0, making it impossible to tell
# whether the agent actually researched the question or just confabulated
# plausible URLs from training data.
_TRAJ_KEY = re.compile(r"^(thought|tool_name|tool_args|observation)_(\d+)$")


def _trajectory_to_tool_calls(trajectory: dict | None) -> list[ToolCallRecord]:
    if not isinstance(trajectory, dict) or not trajectory:
        return []
    # Bucket by step index.
    by_step: dict[int, dict[str, object]] = {}
    for k, v in trajectory.items():
        m = _TRAJ_KEY.match(k)
        if not m:
            continue
        field, idx = m.group(1), int(m.group(2))
        by_step.setdefault(idx, {})[field] = v
    records: list[ToolCallRecord] = []
    for idx in sorted(by_step):
        step = by_step[idx]
        name = step.get("tool_name")
        if not isinstance(name, str) or name == "finish":
            # `finish` is DSPy's synthetic terminator, not a research tool.
            continue
        args = step.get("tool_args")
        if not isinstance(args, dict):
            args = {"_raw": args} if args is not None else {}
        obs = step.get("observation")
        # DSPy stamps tool exceptions as "Execution error in <name>: ..."
        # into the observation field. Pull that into the structured
        # ok=False + error fields so consumers don't have to substring.
        ok = True
        error: str | None = None
        if isinstance(obs, str) and obs.startswith(f"Execution error in {name}:"):
            ok = False
            error = obs.split(":", 1)[1].strip() if ":" in obs else obs
        preview = ""
        if isinstance(obs, str):
            preview = obs[:240].replace("\n", " ")
        elif obs is not None:
            preview = repr(obs)[:240]
        records.append(ToolCallRecord(
            tool=name,
            args=args,
            ok=ok,
            result_preview=preview,
            error=error,
            elapsed_ms=None,  # DSPy doesn't expose per-tool timing today
        ))
    return records


class DspyResearchRunner:
    backend_name = "dspy"

    def __init__(self, *, configure: bool = True) -> None:
        if configure:
            configure_lm()

    async def arun(self, question: str, *, current_date: str) -> ResearchResult:
        return await asyncio.to_thread(self._run_sync, question, current_date)

    def _run_sync(self, question: str, current_date: str) -> ResearchResult:
        agent = build_agent()
        result = agent(current_date=current_date, question=question)
        sources = result.sources if isinstance(result.sources, list) else [result.sources]
        tool_calls = _trajectory_to_tool_calls(getattr(result, "trajectory", None))
        return ResearchResult(
            synthesis=result.synthesis,
            sources=sources,
            backend=self.backend_name,
            tool_calls=tool_calls,
        )
