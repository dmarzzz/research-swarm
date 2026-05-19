import json

from research_agent.log import log_run
from research_agent.types import ToolCallRecord


def test_log_run_preserves_legacy_fields_and_adds_backend_fields(tmp_path) -> None:
    path = log_run(
        question="q",
        synthesis="s",
        sources=["src"],
        backend="codex",
        tool_calls=[ToolCallRecord(tool="web_search", args={"query": "q"}, ok=True)],
        backend_meta={"thread_id": "t"},
        runs_dir=tmp_path,
    )

    data = json.loads(path.read_text())

    assert data["question"] == "q"
    assert data["synthesis"] == "s"
    assert data["sources"] == ["src"]
    assert data["critique"] is None
    assert data["backend"] == "codex"
    assert data["tool_calls"][0]["tool"] == "web_search"
    assert data["backend_meta"] == {"thread_id": "t"}
