"""CLI entry point.

    research-agent "your research question"
    research-agent --parallel "your research question"
    python -m research_agent "your research question"
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import io
import os
import subprocess
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
{DIM}·{RESET}   {CYAN}◆{RESET}   {CYAN}◆{RESET}   {CYAN}◆{RESET}   {DIM}·{RESET}      a research harness that thinks out loud,
  {CYAN}◆{RESET}   {DIM}·{RESET}   {CYAN}◆{RESET}   {DIM}·{RESET}        cites its sources, and remembers what you
     {DIM}·   ·{RESET}              asked last time.
"""
    examples = f"""
{BOLD}try:{RESET}
  {DIM}$ {RESET}research-agent {CYAN}"what is Loopix and how does it beat Tor?"{RESET}
  {DIM}$ {RESET}research-agent {DIM}--parallel{RESET} {CYAN}"survey modern post-quantum signature schemes"{RESET}
  {DIM}$ {RESET}research-agent {DIM}--backend dspy{RESET} {CYAN}"use the original DSPy backend"{RESET}
  {DIM}$ {RESET}research-agent {DIM}--no-critique{RESET} {CYAN}"quick lookup, skip the review"{RESET}

{BOLD}setup:{RESET}
  {DIM}$ {RESET}research-agent doctor      {DIM}# check Codex and DSPy backend readiness{RESET}
  {DIM}$ {RESET}cp .env.example .env       {DIM}# optional DSPy LM config / backend tuning{RESET}
  {DIM}$ {RESET}research-agent --help      {DIM}# all options{RESET}

{DIM}docs: https://github.com/dmarzzz/research-swarm{RESET}
"""
    sys.stderr.write(banner)
    sys.stderr.write(examples)


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "doctor":
        from research_agent.backends.codex import CodexConfig

        config = CodexConfig.from_env()
        return asyncio.run(_doctor(config))

    parser = argparse.ArgumentParser(
        prog="research-agent",
        description=(
            "a research agent that researches a question, cites its "
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
              RA_BACKEND=auto                    default backend; --backend overrides
              CODEX_MODEL=gpt-5.4                optional Codex app-server model
              CODEX_EFFORT=low                   Codex reasoning effort
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
        "--backend",
        choices=["auto", "codex", "dspy"],
        default=None,
        help=(
            "Research backend. Overrides RA_BACKEND from .env/the shell. "
            "auto uses DSPy if configured, else Codex fallback."
        ),
    )
    parser.add_argument(
        "--codex-model",
        default=None,
        help="Codex model override for the codex backend.",
    )
    parser.add_argument(
        "--codex-effort",
        default=None,
        help="Codex reasoning effort override (default CODEX_EFFORT or low).",
    )
    parser.add_argument(
        "--codex-timeout",
        type=float,
        default=None,
        help="Codex turn timeout in seconds (default CODEX_TIMEOUT_SEC or 600).",
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
    args = parser.parse_args(argv)

    if not args.question:
        _welcome()
        return 0

    if args.quiet:
        os.environ["RA_QUIET"] = "1"

    question = " ".join(args.question)
    return asyncio.run(_amain(args, question))


async def _amain(args, question: str) -> int:
    from research_agent.backends.codex import (
        CodexConfig,
        arun_codex_parallel,
        run_codex_critique,
    )
    from research_agent.backends.select import build_runner, choose_backend
    from research_agent.types import ResearchResult

    codex_config = CodexConfig.from_env(
        codex_model=args.codex_model,
        codex_effort=args.codex_effort,
        codex_timeout=args.codex_timeout,
    )
    choice = await choose_backend(args.backend, codex_config=codex_config)

    if choice.selected == "dspy":
        # LM config up front so a missing key surfaces immediately as a
        # friendly error (see SystemExit raised by configure_lm).
        from research_agent.agent import configure_lm

        configure_lm()

    mode = "parallel" if args.parallel else "single"
    mode_label = f"{mode} · {choice.selected}"
    _print_banner(question, mode=mode_label, critic_on=not args.no_critique)
    if args.backend is None or choice.requested == "auto":
        print(f"{DIM}backend{RESET} {choice.selected} · {choice.reason}", file=sys.stderr)
        print(file=sys.stderr)

    if args.parallel:
        if choice.selected == "codex":
            result = await arun_codex_parallel(
                question,
                max_workers=args.workers,
                config=codex_config,
            )
        else:
            from research_agent.parallel import run_parallel

            synthesis, sources, sub_results = await asyncio.to_thread(
                run_parallel,
                question,
                args.workers,
            )
            result = ResearchResult(
                synthesis=synthesis,
                sources=sources,
                backend="dspy",
                sub_results=[
                    {
                        "sub_question": sr.sub_question,
                        "synthesis": sr.synthesis,
                        "sources": sr.sources,
                    }
                    for sr in sub_results
                ],
            )
    else:
        runner = build_runner(choice, codex_config=codex_config)
        result = await runner.arun(question, current_date=date.today().isoformat())

    synthesis = result.synthesis
    sources = result.sources

    _print_output(synthesis, sources)

    critique = None
    if not args.no_critique:
        if choice.selected == "codex":
            try:
                print(f"{DIM}▸ self-critique...{RESET}", file=sys.stderr)
                critique = await run_codex_critique(
                    question,
                    synthesis,
                    sources,
                    config=codex_config,
                )
            except Exception as exc:
                print(f"{YELLOW}critic failed: {exc}{RESET}", file=sys.stderr)
                critique = None
        else:
            critique = await asyncio.to_thread(_run_critique, question, synthesis, sources)
        _print_critique(critique)

    # Persistent run log.
    try:
        from research_agent.log import log_run

        path = log_run(
            question=question,
            synthesis=synthesis,
            sources=sources,
            critique=critique,
            backend=result.backend,
            tool_calls=result.tool_calls,
            sub_results=result.sub_results,
            backend_meta=result.backend_meta,
        )
        print(f"{DIM}→ run saved to {path}{RESET}", file=sys.stderr)
    except Exception as exc:
        print(f"{YELLOW}log_run failed: {exc}{RESET}", file=sys.stderr)

    return 0


async def _doctor(codex_config) -> int:
    from research_agent.backends.codex import codex_smoke_check
    from research_agent.backends.select import choose_backend

    print("research-swarm doctor")
    print()
    try:
        version = subprocess.run(
            [codex_config.codex_bin, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        codex_version = (version.stdout or version.stderr).strip() or f"exit {version.returncode}"
    except Exception as exc:
        codex_version = f"{type(exc).__name__}: {exc}"
    print(f"codex binary: {codex_config.codex_bin}")
    print(f"codex version: {codex_version}")

    ok, message = await codex_smoke_check(codex_config)
    print(f"codex backend: {'ok' if ok else 'unavailable'} · {message}")

    try:
        with contextlib.redirect_stderr(io.StringIO()):
            from research_agent.agent import configure_lm

            configure_lm()
        dspy_message = "ok"
    except SystemExit as exc:
        dspy_message = str(exc).strip().splitlines()[0] if str(exc).strip() else "not configured"
    except Exception as exc:
        dspy_message = f"{type(exc).__name__}: {exc}"
    print(f"dspy backend: {dspy_message}")

    choice = await choose_backend(None, codex_config=codex_config)
    print(f"default backend: {choice.selected} · {choice.reason}")
    return 0 if ok or dspy_message == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
