import asyncio

from research_agent.parallel import arun_parallel
from research_agent.types import ResearchResult


class FakeRunner:
    async def arun(self, question: str, *, current_date: str) -> ResearchResult:
        return ResearchResult(
            synthesis=f"synthesis for {question}",
            sources=[f"source:{question}"],
            backend="fake",
        )


def test_arun_parallel_uses_runner_factory_and_merge() -> None:
    async def run() -> ResearchResult:
        return await arun_parallel(
            "question",
            runner_factory=FakeRunner,
            max_workers=2,
            decompose_fn=lambda q: ["a", "b"],
            merge_fn=lambda **kwargs: ResearchResult(
                synthesis="merged: " + ", ".join(kwargs["sub_syntheses"]),
                sources=kwargs["all_sources"],
                backend="fake",
            ),
        )

    result = asyncio.run(run())

    assert result.synthesis == "merged: synthesis for a, synthesis for b"
    assert result.sources == ["source:a", "source:b"]
    assert [item["sub_question"] for item in result.sub_results] == ["a", "b"]
