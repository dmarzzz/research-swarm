"""DSPy backend wrapper.

The public DSPy compatibility surface remains in :mod:`research_agent.agent`.
This module only adapts it to the backend-neutral runner interface.
"""

from __future__ import annotations

import asyncio

from research_agent.agent import build_agent, configure_lm
from research_agent.types import ResearchResult


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
        return ResearchResult(
            synthesis=result.synthesis,
            sources=sources,
            backend=self.backend_name,
        )
