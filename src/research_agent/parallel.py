"""Parallel sub-question decomposition and fan-out.

STORM-inspired pattern: decompose a research question into independent
sub-questions, run a ReAct agent on each in parallel, then merge the
sub-syntheses into a single grounded answer.
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from typing import NamedTuple

import dspy

from research_agent.agent import ResearchTask, build_agent


# ── Decomposition signature ───────────────────────────────────────────


class DecomposeQuestion(dspy.Signature):
    """Break a complex research question into 3–5 independent sub-questions
    that, taken together, would fully answer the original. Each sub-question
    should be self-contained (answerable without seeing the others) and
    cover a distinct angle or facet. Prefer concrete, searchable sub-questions
    over vague ones."""

    question: str = dspy.InputField(desc="The original research question.")
    sub_questions: list[str] = dspy.OutputField(
        desc=(
            "3–5 independent sub-questions. Each must be self-contained, "
            "specific, and searchable. Together they should cover the full "
            "scope of the original question."
        )
    )


# ── Merge signature ──────────────────────────────────────────────────


class MergeSyntheses(dspy.Signature):
    """Merge several sub-syntheses into one cohesive, grounded answer.
    Deduplicate overlapping content. Preserve every inline citation
    ([arXiv:id] or [owner/repo]) from the sub-syntheses. Use Markdown
    structure (headings, tables) for readability. If sub-syntheses
    contradict each other, note the disagreement rather than silently
    picking one side."""

    original_question: str = dspy.InputField(
        desc="The original research question the user asked."
    )
    sub_questions: list[str] = dspy.InputField(
        desc="The sub-questions that were researched in parallel."
    )
    sub_syntheses: list[str] = dspy.InputField(
        desc="The synthesis produced for each sub-question, in the same order."
    )
    all_sources: list[str] = dspy.InputField(
        desc="Flat deduplicated list of all sources across sub-syntheses."
    )

    synthesis: str = dspy.OutputField(
        desc=(
            "A single cohesive answer to the original question, merging "
            "all sub-syntheses. Use Markdown. Preserve all citations. "
            "Deduplicate content. Note contradictions."
        )
    )
    sources: list[str] = dspy.OutputField(
        desc="Final deduplicated list of all cited sources."
    )


# ── Sub-result container ─────────────────────────────────────────────


class SubResult(NamedTuple):
    sub_question: str
    synthesis: str
    sources: list[str]


# ── Public API ────────────────────────────────────────────────────────


def decompose(question: str) -> list[str]:
    """Decompose a question into sub-questions."""
    decomposer = dspy.ChainOfThought(DecomposeQuestion)
    result = decomposer(question=question)
    subs = result.sub_questions
    # Clamp to 3–5.
    if len(subs) < 2:
        return [question]
    return subs[:5]


def _run_sub_question(sub_q: str) -> SubResult:
    """Run a single ReAct agent on one sub-question. Thread-safe because
    each call builds its own module and DSPy's LM is thread-safe (HTTP)."""
    agent = build_agent()
    result = agent(current_date=date.today().isoformat(), question=sub_q)
    sources = result.sources if isinstance(result.sources, list) else [result.sources]
    return SubResult(sub_question=sub_q, synthesis=result.synthesis, sources=sources)


def run_parallel(question: str, max_workers: int | None = None) -> tuple[str, list[str], list[SubResult]]:
    """Decompose → fan-out → merge.  Returns (synthesis, sources, sub_results)."""
    workers = max_workers or int(os.environ.get("PARALLEL_WORKERS", "3"))

    # 1. Decompose
    print(f"\n▸ decomposing question into sub-questions...", file=sys.stderr)
    sub_questions = decompose(question)
    for i, sq in enumerate(sub_questions, 1):
        print(f"  {i}. {sq}", file=sys.stderr)
    print(file=sys.stderr)

    # 2. Fan out
    sub_results: list[SubResult] = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(_run_sub_question, sq): sq for sq in sub_questions
        }
        for future in as_completed(futures):
            sq = futures[future]
            try:
                sr = future.result()
                sub_results.append(sr)
                print(f"  ✓ done: {sq[:70]}...", file=sys.stderr)
            except Exception as exc:
                print(f"  ✗ failed: {sq[:70]}... ({exc})", file=sys.stderr)

    if not sub_results:
        raise RuntimeError("All sub-questions failed.")

    # Keep original order for the merge prompt.
    order = {sq: i for i, sq in enumerate(sub_questions)}
    sub_results.sort(key=lambda sr: order.get(sr.sub_question, 99))

    # 3. Merge
    print(f"\n▸ merging {len(sub_results)} sub-syntheses...", file=sys.stderr)
    all_sources = _dedup_sources(
        s for sr in sub_results for s in sr.sources
    )
    merger = dspy.ChainOfThought(MergeSyntheses)
    merged = merger(
        original_question=question,
        sub_questions=[sr.sub_question for sr in sub_results],
        sub_syntheses=[sr.synthesis for sr in sub_results],
        all_sources=all_sources,
    )

    final_sources = merged.sources if isinstance(merged.sources, list) else [merged.sources]
    return merged.synthesis, final_sources, sub_results


def _dedup_sources(sources) -> list[str]:
    """Deduplicate while preserving order."""
    seen: set[str] = set()
    result: list[str] = []
    for s in sources:
        if s not in seen:
            seen.add(s)
            result.append(s)
    return result
