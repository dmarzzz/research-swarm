"""Verifies the DSPy backend extracts ReAct trajectories into structured
ToolCallRecords. Prior to this, every dspy run wrote tool_calls=[] to
the trace JSON even when the agent actually called tools — making it
look like the model answered from memory ("violet trace" bug).

Pure-Python test: builds a fake trajectory dict in DSPy's wire format
and asserts the conversion + edge cases. No LM, no network.
"""

from __future__ import annotations

import pytest

from research_agent.backends.dspy import _trajectory_to_tool_calls


def test_empty_trajectory_returns_empty_list():
    assert _trajectory_to_tool_calls(None) == []
    assert _trajectory_to_tool_calls({}) == []


def test_trajectory_drops_synthetic_finish_step():
    trajectory = {
        "thought_0": "I should answer directly.",
        "tool_name_0": "finish",
        "tool_args_0": {},
        "observation_0": "Completed.",
    }
    assert _trajectory_to_tool_calls(trajectory) == []


def test_single_successful_tool_call_extracted():
    trajectory = {
        "thought_0": "Search for Loopix.",
        "tool_name_0": "web_search",
        "tool_args_0": {"query": "Loopix anonymous communication"},
        "observation_0": "[web_search NETWORK · ddg:5 · merged=5]\n- Loopix ...",
        "thought_1": "I have what I need.",
        "tool_name_1": "finish",
        "tool_args_1": {},
        "observation_1": "Done.",
    }
    records = _trajectory_to_tool_calls(trajectory)
    assert len(records) == 1
    r = records[0]
    assert r.tool == "web_search"
    assert r.args == {"query": "Loopix anonymous communication"}
    assert r.ok is True
    assert r.error is None
    assert "Loopix" in r.result_preview
    assert r.elapsed_ms is None


def test_tool_exception_recorded_as_not_ok():
    trajectory = {
        "thought_0": "Try arxiv.",
        "tool_name_0": "arxiv_search",
        "tool_args_0": {"query": "x"},
        "observation_0": "Execution error in arxiv_search: ConnectionError: timeout",
    }
    records = _trajectory_to_tool_calls(trajectory)
    assert len(records) == 1
    assert records[0].ok is False
    assert "ConnectionError" in records[0].error


def test_steps_returned_in_index_order_regardless_of_dict_order():
    # Python dicts preserve insertion order — feed out of order to be safe.
    trajectory = {
        "tool_name_2": "fetch_url",
        "tool_args_2": {"url": "https://x/3"},
        "observation_2": "third",
        "tool_name_0": "web_search",
        "tool_args_0": {"query": "a"},
        "observation_0": "first",
        "tool_name_1": "web_search",
        "tool_args_1": {"query": "b"},
        "observation_1": "second",
    }
    records = _trajectory_to_tool_calls(trajectory)
    assert [r.tool for r in records] == ["web_search", "web_search", "fetch_url"]
    assert [r.args["query"] for r in records[:2]] == ["a", "b"]
    assert records[2].args["url"] == "https://x/3"


def test_non_dict_tool_args_wrapped_under_raw():
    trajectory = {
        "tool_name_0": "weird_tool",
        "tool_args_0": "stringified-args-from-buggy-pred",
        "observation_0": "ok",
    }
    records = _trajectory_to_tool_calls(trajectory)
    assert records[0].args == {"_raw": "stringified-args-from-buggy-pred"}


def test_result_preview_is_truncated_and_single_line():
    long = "line1\nline2\n" + ("x" * 500)
    trajectory = {
        "tool_name_0": "fetch_url",
        "tool_args_0": {"url": "x"},
        "observation_0": long,
    }
    records = _trajectory_to_tool_calls(trajectory)
    assert len(records[0].result_preview) <= 240
    assert "\n" not in records[0].result_preview
