"""Seed research questions for exercising the agent.

Run the agent on these, mark which outputs are accepted vs rejected, and
use the accepted ones as a trainset when you eventually compile the agent
with MIPROv2. ~20 accepted examples is usually enough.

Usage:
    python -c "from examples.seed_questions import SEED_QUESTIONS; print('\\n'.join(SEED_QUESTIONS))"
    # or just import and iterate
"""

from __future__ import annotations

SEED_QUESTIONS: list[str] = [
    # ── direct GPTSwarm lineage ─────────────────────────────────────────
    "What's the precise difference between AFlow's MCTS workflow search and GPTSwarm's REINFORCE edge optimization, and which performs better on HumanEval and MATH?",
    "How does MaAS's agentic supernet differ structurally from a single-graph optimizer like GPTSwarm, and what does it report for inference cost vs accuracy?",
    "Which 2025 papers extend GPTSwarm with distributions over agent architectures rather than searching for a single best graph?",
    "What's the search space in ADAS's meta-agent framework vs AgentSquare's typed modular slots, and what are the trade-offs in practice?",

    # ── second wave refinements ─────────────────────────────────────────
    "How does A²Flow learn its own operator vocabulary, and does it actually outperform fixed-operator workflow search on the papers' benchmarks?",
    "What is DebFlow's multi-agent debate mechanism for proposing workflow edits, and what gains does it report over REINFORCE- or MCTS-based baselines?",
    "Has anyone extended G-Designer's VGAE-based topology generation to larger agent counts, and are there open repos?",

    # ── umbrella / EvoAgentX ────────────────────────────────────────────
    "Which optimizers does EvoAgentX integrate as of mid-2026, and what are its reported gains on HotPotQA, MATH, and MBPP?",
    "Is there any public framework that combines MaAS-style supernet sampling with AFlow-style MCTS in a single training loop?",

    # ── sibling line (inside-node optimization) ─────────────────────────
    "What's the current best prompt optimizer in DSPy (MIPROv2, GEPA, COPRO, SIMBA), and what are the conditions under which each wins?",
    "How does TextGrad's backward textual-gradient step actually work mechanically, and what's the per-step LLM overhead?",
    "What does Microsoft Trace optimize that DSPy can't, and is the additional complexity worth it for a typical research pipeline?",

    # ── meta-questions about the field ──────────────────────────────────
    "Which of the GPTSwarm-lineage frameworks are still actively maintained as of 2026, and which have stalled?",
    "What's the current state-of-the-art on HotPotQA among agentic frameworks, and which framework holds it?",
    "Have any of the GPTSwarm-lineage frameworks been adopted in production by a real company, or are they all research-only?",
]
