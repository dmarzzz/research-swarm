"""CLI entry point.

    research-agent "your research question"
    research-agent --parallel "your research question"
    python -m research_agent "your research question"
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from datetime import date

from research_agent import __version__


# ── Terminal output helpers ───────────────────────────────────────────────


def _use_color() -> bool:
    """Emit ANSI color only when stdout looks like a real terminal and
    the user hasn't opted out via NO_COLOR or --no-color."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("RA_NO_COLOR") in ("1", "true", "yes"):
        return False
    return sys.stdout.isatty()


def _c(code: str) -> str:
    return code if _use_color() else ""


DIM = _c("\033[2m")
BOLD = _c("\033[1m")
CYAN = _c("\033[36m")
GREEN = _c("\033[32m")
YELLOW = _c("\033[33m")
MAGENTA = _c("\033[35m")
RESET = _c("\033[0m")


def _print_banner(question: str, mode: str, critic_on: bool) -> None:
    """Small boxed banner at the start of a run.

    Aligns the label column manually (2-space gutter after label) and
    skips trying to pad the right edge, since ANSI codes break width
    math and nobody reads the right edge anyway.
    """
    q = question if len(question) <= 64 else question[:61] + "..."
    crit = "critic on" if critic_on else "critic off"
    mode_line = f"{mode} · {crit}"

    print(f"{DIM}┌─{RESET} {CYAN}research-swarm{RESET} {DIM}{'─' * 60}┐{RESET}", file=sys.stderr)
    print(f"{DIM}│{RESET} {BOLD}{'mode':<10}{RESET}{mode_line}", file=sys.stderr)
    print(f"{DIM}│{RESET} {BOLD}{'question':<10}{RESET}{q}", file=sys.stderr)
    print(f"{DIM}└{'─' * 76}┘{RESET}", file=sys.stderr)
    print("", file=sys.stderr)


def _print_output(synthesis: str, sources: list[str]) -> None:
    print()
    print(f"{BOLD}╭─ synthesis {RESET}" + "─" * 63 + "╮")
    for line in synthesis.splitlines() or [""]:
        # Wrap long lines at 74 chars for readability
        for wrap in textwrap.wrap(line, width=74) or [""]:
            print(f"{DIM}│{RESET} {wrap}")
    print(f"{BOLD}╰{RESET}" + "─" * 75 + "╯")
    print()
    print(f"{BOLD}sources:{RESET}")
    for s in sources:
        print(f"  {DIM}·{RESET} {s}")
    print()


def _run_critique(question: str, synthesis: str, sources: list[str]):
    """Run the self-critique pass. Returns the critique or None."""
    from research_agent.critic import build_critic

    try:
        print(f"{DIM}▸ self-critique...{RESET}", file=sys.stderr)
        critic = build_critic()
        return critic(
            current_date=date.today().isoformat(),
            question=question,
            synthesis=synthesis,
            sources=sources,
        )
    except Exception as exc:
        print(f"{YELLOW}critic failed: {exc}{RESET}", file=sys.stderr)
        return None


def _score_glyph(score: int) -> str:
    """Visualize 1-5 grounding score as filled circles."""
    filled = "●" * max(0, min(5, score))
    empty = "○" * (5 - max(0, min(5, score)))
    color = GREEN if score >= 4 else (YELLOW if score >= 3 else MAGENTA)
    return f"{color}{filled}{DIM}{empty}{RESET}"


def _print_critique(critique) -> None:
    if critique is None:
        return
    score = getattr(critique, "grounding_score", 0)
    print(f"{BOLD}critique:{RESET}")
    print(f"  {DIM}grounding{RESET}  {_score_glyph(score)}  {score}/5")
    print(f"  {DIM}verdict{RESET}    {critique.overall_verdict}")
    gaps = critique.coverage_gaps or []
    if gaps:
        print(f"  {DIM}gaps{RESET}")
        for g in gaps:
            print(f"    {YELLOW}·{RESET} {g}")
    errs = critique.likely_errors or []
    if errs:
        print(f"  {DIM}errors{RESET}")
        for e in errs:
            print(f"    {MAGENTA}·{RESET} {e}")
    tweak = (critique.suggested_prompt_tweak or "").strip()
    if tweak:
        print(f"  {DIM}next-prompt tweak{RESET}")
        print(f"    {CYAN}\"{tweak}\"{RESET}")
    print()


def _welcome() -> None:
    """Shown when the user invokes `research-agent` with no question."""
    banner = f"""
     {DIM}·   ·{RESET}
  {DIM}·{RESET}  {CYAN}◆{RESET}    {DIM}·   ·{RESET}        {BOLD}research-swarm{RESET}  {DIM}v{__version__}{RESET}
{DIM}·{RESET}   {CYAN}◆{RESET}   {CYAN}◆{RESET}   {CYAN}◆{RESET}   {DIM}·{RESET}      a DSPy ReAct agent that thinks out loud,
  {CYAN}◆{RESET}   {DIM}·{RESET}   {CYAN}◆{RESET}   {DIM}·{RESET}        cites its sources, and remembers what you
     {DIM}·   ·{RESET}              asked last time.
"""
    examples = f"""
{BOLD}try:{RESET}
  {DIM}$ {RESET}research-agent {CYAN}"what is Loopix and how does it beat Tor?"{RESET}
  {DIM}$ {RESET}research-agent {DIM}--parallel{RESET} {CYAN}"survey modern post-quantum signature schemes"{RESET}
  {DIM}$ {RESET}research-agent {DIM}--no-critique{RESET} {CYAN}"quick lookup, skip the review"{RESET}

{BOLD}setup:{RESET}
  {DIM}$ {RESET}cp .env.example .env       {DIM}# pick an LM (Ollama, Anthropic, OpenAI, ...){RESET}
  {DIM}$ {RESET}research-agent --help      {DIM}# all options{RESET}

{DIM}docs: https://github.com/dmarzzz/research-swarm{RESET}
"""
    sys.stderr.write(banner)
    sys.stderr.write(examples)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="research-agent",
        description=(
            "a DSPy ReAct agent that researches a question, cites its "
            "sources, grows a local archive as it reads, and self-critiques "
            "its answers."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """
            examples:
              research-agent "what is Loopix and how does it beat Tor?"
              research-agent --parallel "survey modern post-quantum signatures"
              research-agent --no-critique "quick lookup, skip review"

            common env vars (put in .env):
              LM_MODEL=ollama/qwen3:35b        fully-local LM, no key needed
              LM_MODEL=anthropic/...           + ANTHROPIC_API_KEY
              RA_WORLD_KNOWLEDGE_DIR=/path     override default ~/world_knowledge/
              RA_QUIET=1                       suppress the live tool trace
              GITHUB_TOKEN=ghp_...             raises GitHub API limit (60 → 5000/hr)
            """
        ),
    )
    parser.add_argument(
        "question", nargs="*",
        help="The research question (required unless you just want the welcome screen).",
    )
    parser.add_argument(
        "--parallel", "-p", action="store_true",
        help="Decompose into sub-questions and research them in parallel (STORM pattern).",
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=None,
        help="Parallel worker count (default 3, or PARALLEL_WORKERS env).",
    )
    parser.add_argument(
        "--no-critique", action="store_true",
        help="Skip the self-critique pass.",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress the live tool-call trace (useful for scripts).",
    )
    parser.add_argument(
        "--version", action="version", version=f"research-swarm {__version__}",
    )
    args = parser.parse_args()

    if not args.question:
        _welcome()
        return 0

    if args.quiet:
        os.environ["RA_QUIET"] = "1"

    question = " ".join(args.question)

    # LM config up front so a missing key surfaces immediately as a
    # friendly error (see SystemExit raised by configure_lm).
    from research_agent.agent import configure_lm

    configure_lm()

    mode = "parallel" if args.parallel else "single"
    _print_banner(question, mode=mode, critic_on=not args.no_critique)

    if args.parallel:
        from research_agent.parallel import run_parallel

        synthesis, sources, _ = run_parallel(question, max_workers=args.workers)
    else:
        from research_agent.agent import build_agent

        agent = build_agent()
        result = agent(current_date=date.today().isoformat(), question=question)
        synthesis = result.synthesis
        sources = result.sources if isinstance(result.sources, list) else [result.sources]

    _print_output(synthesis, sources)

    critique = None
    if not args.no_critique:
        critique = _run_critique(question, synthesis, sources)
        _print_critique(critique)

    # Persistent run log.
    try:
        from research_agent.log import log_run

        path = log_run(
            question=question,
            synthesis=synthesis,
            sources=sources,
            critique=critique,
        )
        print(f"{DIM}→ run saved to {path}{RESET}", file=sys.stderr)
    except Exception as exc:
        print(f"{YELLOW}log_run failed: {exc}{RESET}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
