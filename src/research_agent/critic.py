"""Self-critique module.

After the ReAct research agent produces a synthesis, this module reads it
back and scores it against a rubric. The same model that produced the
synthesis is producing the critique, so expect shallower findings than
an external judge would give — but it's the cheapest way to get structured
self-reflection, and every critique gets logged alongside the run for
later consumption by an LLM-as-judge metric or a MIPRO compile loop.
"""

from __future__ import annotations

import dspy


class Critique(dspy.Signature):
    """Review a research synthesis against a rubric. Be specific and
    unsparing — name actual missing items, flag actual likely-wrong cells,
    and propose ONE concrete sentence the user could add to their next
    prompt to fix the biggest issue. Do not write generic advice. If
    the output looks fine, say so plainly — do not manufacture problems.

    IMPORTANT: Use the current_date field to judge temporal plausibility.
    An arXiv ID like 2602.XXXXX means February 2026 — check whether that
    is before or after today's date before calling it "temporally
    impossible." Do NOT assume the current year is 2025."""

    current_date: str    = dspy.InputField(desc="Today's date in YYYY-MM-DD format. Use this for temporal plausibility checks on arXiv IDs and publication dates.")
    question:  str       = dspy.InputField(desc="The original research question.")
    synthesis: str       = dspy.InputField(desc="The agent's synthesis / answer.")
    sources:   list[str] = dspy.InputField(desc="The sources cited in the synthesis.")

    coverage_gaps: list[str] = dspy.OutputField(
        desc=(
            "Specific named items (frameworks, papers, angles, dimensions) "
            "that should plausibly be in the synthesis but aren't. Name "
            "them with specifics — 'MaAS (arXiv:2502.04180)' not "
            "'more optimization frameworks'. Empty list if coverage is fine."
        )
    )
    likely_errors: list[str] = dspy.OutputField(
        desc=(
            "Specific cells, claims, or statements that look wrong, "
            "unverified, or inferred rather than sourced. Quote the exact "
            "claim when possible. Empty list if nothing looks wrong."
        )
    )
    grounding_score: int = dspy.OutputField(
        desc=(
            "Integer 1-5. 1 = mostly unsourced. 3 = half the claims "
            "cited. 5 = every non-trivial claim has an inline citation "
            "and all cited sources appear real."
        )
    )
    suggested_prompt_tweak: str = dspy.OutputField(
        desc=(
            "One concrete sentence the user could add to their next "
            "prompt to fix the biggest remaining issue. Must be quotable "
            "and specific, not vague advice. Empty string if the output "
            "genuinely doesn't need improvement."
        )
    )
    overall_verdict: str = dspy.OutputField(
        desc="One short sentence summarizing strengths and weaknesses."
    )


def build_critic() -> dspy.Module:
    """Build the self-critique module (ChainOfThought wrapped Critique)."""
    return dspy.ChainOfThought(Critique)
