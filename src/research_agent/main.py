"""CLI entry point.

    research-agent "your research question"
    research-agent --parallel "your research question"
    python -m research_agent "your research question"
"""

from __future__ import annotations

import argparse
import sys
from datetime import date

from research_agent.agent import build_agent, configure_lm
from research_agent.critic import build_critic
from research_agent.log import log_run


def _print_output(synthesis: str, sources: list[str]) -> None:
    print("=" * 78)
    print("SYNTHESIS")
    print("=" * 78)
    print(synthesis)
    print()
    print("=" * 78)
    print("SOURCES")
    print("=" * 78)
    for s in sources:
        print(f"  · {s}")
    print()


def _run_critique(question: str, synthesis: str, sources: list[str]):
    """Run the self-critique pass. Returns the critique or None."""
    try:
        print("▸ running self-critique...", file=sys.stderr)
        critic = build_critic()
        return critic(
            current_date=date.today().isoformat(),
            question=question,
            synthesis=synthesis,
            sources=sources,
        )
    except Exception as exc:
        print(f"critic failed: {exc}", file=sys.stderr)
        return None


def _print_critique(critique) -> None:
    if critique is None:
        return
    print("=" * 78)
    print("CRITIQUE")
    print("=" * 78)
    print(f"Verdict:          {critique.overall_verdict}")
    print(f"Grounding score:  {critique.grounding_score}/5")
    print()
    gaps = critique.coverage_gaps or []
    if gaps:
        print("Coverage gaps:")
        for g in gaps:
            print(f"  · {g}")
    else:
        print("Coverage gaps:    none detected")
    print()
    errs = critique.likely_errors or []
    if errs:
        print("Likely errors:")
        for e in errs:
            print(f"  · {e}")
    else:
        print("Likely errors:    none detected")
    print()
    tweak = critique.suggested_prompt_tweak or ""
    if tweak.strip():
        print("Next-prompt tweak:")
        print(f'  "{tweak}"')
    else:
        print("Next-prompt tweak: — (critic had no suggestion)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description="DSPy research agent for surveying LLM agent-frameworks literature.",
    )
    parser.add_argument("question", nargs="+", help="The research question.")
    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Decompose the question into sub-questions and research them in parallel.",
    )
    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=None,
        help="Number of parallel workers (default: 3, or PARALLEL_WORKERS env var).",
    )
    parser.add_argument(
        "--no-critique",
        action="store_true",
        help="Skip the self-critique pass.",
    )
    args = parser.parse_args()
    question = " ".join(args.question)

    configure_lm()

    if args.parallel:
        from research_agent.parallel import run_parallel

        synthesis, sources, sub_results = run_parallel(
            question, max_workers=args.workers
        )
    else:
        agent = build_agent()
        print(f"\n▸ researching: {question}\n", file=sys.stderr)
        result = agent(current_date=date.today().isoformat(), question=question)
        synthesis = result.synthesis
        sources = result.sources if isinstance(result.sources, list) else [result.sources]

    _print_output(synthesis, sources)

    # Self-critique pass.
    critique = None
    if not args.no_critique:
        critique = _run_critique(question, synthesis, sources)
        _print_critique(critique)

    # Log the run.
    try:
        path = log_run(
            question=question,
            synthesis=synthesis,
            sources=sources,
            critique=critique,
        )
        print(f"→ run saved to {path}", file=sys.stderr)
    except Exception as exc:
        print(f"log_run failed: {exc}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
