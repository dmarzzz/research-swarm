import asyncio
import json
from pathlib import Path

import pytest

from research_agent.backends.codex import CodexConfig, CodexResearchRunner, parse_codex_action
from research_agent.tool_registry import ToolRegistry


class FakeTurn:
    def __init__(self, text: str, turn_id: str = "turn") -> None:
        self.final_text = text
        self.turn_id = turn_id


class FakeThread:
    def __init__(self, replies: list[str]) -> None:
        self.replies = replies
        self.archived = False

    async def run_turn(self, *args, **kwargs) -> FakeTurn:
        if not self.replies:
            raise AssertionError("No fake replies left")
        return FakeTurn(self.replies.pop(0), turn_id=f"turn-{len(self.replies)}")

    async def archive(self) -> None:
        self.archived = True


class FakeSession:
    def __init__(self, replies: list[str]) -> None:
        self.thread = FakeThread(replies)

    async def start_thread(self, *args, **kwargs) -> FakeThread:
        return self.thread


def lookup(query: str) -> str:
    """Look up a fake source."""
    return f"source for {query}"


def action(action_name: str, tool: str = "", args: dict | None = None, synthesis: str = "", sources=None) -> str:
    return json.dumps(
        {
            "action": action_name,
            "tool": tool,
            "args": json.dumps(args or {}),
            "synthesis": synthesis,
            "sources": sources or [],
        }
    )


def config() -> CodexConfig:
    return CodexConfig(
        codex_bin="codex",
        model=None,
        effort="low",
        timeout_sec=10,
        rpc_log=False,
        stdio_limit=1024 * 1024,
        tool_result_max_chars=1000,
        context_max_chars=4000,
    )


def test_parse_codex_action_accepts_fenced_json() -> None:
    parsed = parse_codex_action(f"```json\n{action('finish', synthesis='x', sources=['s'])}\n```")

    assert parsed.action == "finish"
    assert parsed.sources == ["s"]


def test_parse_codex_action_accepts_json_with_trailing_text() -> None:
    parsed = parse_codex_action(
        action("finish", synthesis="x", sources=["s"]) + "\n\nExtra note."
    )

    assert parsed.action == "finish"
    assert parsed.synthesis == "x"


def test_parse_codex_action_rejects_bad_args() -> None:
    bad = json.dumps(
        {"action": "call_tool", "tool": "lookup", "args": "[]", "synthesis": "", "sources": []}
    )

    with pytest.raises(ValueError, match="args"):
        parse_codex_action(bad)


def test_codex_runner_executes_tool_then_finishes(tmp_path: Path) -> None:
    session = FakeSession(
        [
            action("call_tool", tool="lookup", args={"query": "alpha"}),
            action("finish", synthesis="Answer [source]", sources=["source"]),
        ]
    )
    runner = CodexResearchRunner(
        config=config(),
        session=session,
        cwd=tmp_path,
        registry=ToolRegistry([lookup]),
    )

    result = asyncio.run(runner.arun("question", current_date="2026-05-19"))

    assert result.synthesis == "Answer [source]"
    assert result.sources == ["source"]
    assert result.tool_calls[0].tool == "lookup"
    assert result.tool_calls[0].ok is True
    assert session.thread.archived is True


def test_codex_runner_records_unknown_tool_and_recovers(tmp_path: Path) -> None:
    session = FakeSession(
        [
            action("call_tool", tool="missing", args={"query": "alpha"}),
            action("finish", synthesis="Recovered", sources=[]),
        ]
    )
    runner = CodexResearchRunner(
        config=config(),
        session=session,
        cwd=tmp_path,
        registry=ToolRegistry([lookup]),
    )

    result = asyncio.run(runner.arun("question", current_date="2026-05-19"))

    assert result.synthesis == "Recovered"
    assert result.tool_calls[0].ok is False
    assert "Unknown tool" in (result.tool_calls[0].error or "")


def test_codex_runner_exhausts_max_iters(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MAX_ITERS", "1")
    session = FakeSession([action("call_tool", tool="lookup", args={"query": "alpha"})])
    runner = CodexResearchRunner(
        config=config(),
        session=session,
        cwd=tmp_path,
        registry=ToolRegistry([lookup]),
    )

    with pytest.raises(RuntimeError, match="max iterations"):
        asyncio.run(runner.arun("question", current_date="2026-05-19"))
