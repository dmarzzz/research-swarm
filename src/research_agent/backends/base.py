"""Backend protocol."""

from __future__ import annotations

from typing import Protocol

from research_agent.types import ResearchResult


class ResearchRunner(Protocol):
    backend_name: str

    async def arun(self, question: str, *, current_date: str) -> ResearchResult:
        """Run one research question and return a backend-neutral result."""
