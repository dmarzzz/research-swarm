import asyncio
import os

import pytest

from research_agent.backends.codex import CodexConfig, CodexResearchRunner, codex_smoke_check
from research_agent.tool_registry import ToolRegistry


pytestmark = pytest.mark.skipif(
    os.environ.get("RA_RUN_CODEX_INTEGRATION") != "1",
    reason="set RA_RUN_CODEX_INTEGRATION=1 to run real codex app-server tests",
)


def lookup(query: str) -> str:
    """Return a deterministic integration-test source for the query."""
    return f"integration source for {query}"


def test_real_codex_structured_smoke() -> None:
    ok, message = asyncio.run(codex_smoke_check(CodexConfig.from_env(codex_timeout=120)))

    assert ok, message


def test_real_codex_one_tool_call(tmp_path) -> None:
    runner = CodexResearchRunner(
        config=CodexConfig.from_env(codex_timeout=120),
        cwd=tmp_path,
        registry=ToolRegistry([lookup]),
    )

    result = asyncio.run(
        runner.arun(
            "Call lookup exactly once with query alpha, then finish with a one-sentence answer.",
            current_date="2026-05-19",
        )
    )

    assert result.tool_calls
    assert result.tool_calls[0].tool == "lookup"
    assert result.sources == [] or isinstance(result.sources[0], str)
