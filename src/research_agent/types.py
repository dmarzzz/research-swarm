"""Shared data types for research backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ToolCallRecord:
    """One Python-owned research tool invocation."""

    tool: str
    args: dict[str, Any]
    ok: bool
    result_preview: str = ""
    error: str | None = None
    elapsed_ms: int | None = None


@dataclass(slots=True)
class ResearchResult:
    """Backend-neutral result returned by a research runner."""

    synthesis: str
    sources: list[str]
    backend: str
    tool_calls: list[ToolCallRecord] = field(default_factory=list)
    sub_results: list[dict[str, Any]] = field(default_factory=list)
    backend_meta: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CritiqueResult:
    """Structured critique fields shared by DSPy and Codex critics."""

    coverage_gaps: list[str]
    likely_errors: list[str]
    grounding_score: int
    suggested_prompt_tweak: str
    overall_verdict: str
