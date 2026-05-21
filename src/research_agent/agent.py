"""The DSPy research agent.

Deliberately the un-optimized version: one Signature, one ReAct module, two
tools. Use it normally first — collect 15–30 real research tasks plus your
thumbs-up/down — then compile with MIPROv2 (see examples/compile.py — not
yet written) to tune the prompts for your research style.
"""

from __future__ import annotations

import functools
import os
import sys
import time

import dspy

from research_agent.tools import (
    arxiv_fetch_paper,
    arxiv_search,
    expanded_search,
    extract_links,
    fetch_url,
    fetch_urls_parallel,
    github_search,
    local_search,
    nitter_search,
    semantic_scholar_search,
    verify_arxiv_citations,
    web_search,
)


# ── live tool trace ───────────────────────────────────────────────────────


def _short(x, n: int = 72) -> str:
    """Compact repr, clamped to n chars."""
    s = repr(x) if not isinstance(x, str) else x
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def _trace_tool(fn):
    """Wrap a ReAct tool so the CLI shows a live call line on stderr.

    Default: on. Suppress with `RA_QUIET=1` for scripts / batch runs.
    Preserves `__name__` and `__doc__` so DSPy's ReAct prompt-builder
    still reads the tool's docstring correctly.
    """
    name = fn.__name__

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        if os.environ.get("RA_QUIET") not in ("1", "true", "yes"):
            parts = [_short(a, 56) for a in args]
            parts += [f"{k}={_short(v, 40)}" for k, v in kwargs.items()]
            sig = ", ".join(parts)
            print(f"  ▸ {name}({sig})", file=sys.stderr, flush=True)
            t0 = time.time()
        try:
            out = fn(*args, **kwargs)
        except Exception as exc:
            if os.environ.get("RA_QUIET") not in ("1", "true", "yes"):
                print(f"    ↳ error · {type(exc).__name__}: {exc}", file=sys.stderr, flush=True)
            raise
        if os.environ.get("RA_QUIET") not in ("1", "true", "yes"):
            ms = int((time.time() - t0) * 1000)
            head = (out or "").splitlines()[0] if isinstance(out, str) else ""
            head = head.strip().strip("[]")[:80] if head else ""
            suffix = f" · {head}" if head else ""
            print(f"    ↳ {ms}ms{suffix}", file=sys.stderr, flush=True)
        return out

    return wrapped


# ── LM configuration ──────────────────────────────────────────────────────


def configure_lm() -> None:
    """Configure DSPy's global LM from environment variables.

    Supports any provider that litellm understands.  Examples:

        LM_MODEL=ollama/llama3.2                        # local Ollama
        LM_MODEL=openai/my-model  LM_API_BASE=http://localhost:8000/v1  # vLLM / llama.cpp
        LM_MODEL=anthropic/claude-sonnet-4-6  LM_API_KEY=sk-ant-...     # Anthropic (default)

    Falls back to ANTHROPIC_MODEL / ANTHROPIC_API_KEY for backward compat.
    """
    # --- resolve model identifier ------------------------------------
    model = os.environ.get("LM_MODEL")
    if not model:
        # Backward compat: build "anthropic/{ANTHROPIC_MODEL}" if the
        # new generic var isn't set.
        anthropic_model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        model = f"anthropic/{anthropic_model}"

    # --- resolve optional api key / base url -------------------------
    api_key = os.environ.get("LM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    api_base = os.environ.get("LM_API_BASE")

    # Only require a key for providers that need one.
    # Ollama and other local servers don't.
    provider = model.split("/", 1)[0] if "/" in model else ""
    needs_key = provider not in ("ollama", "ollama_chat") and not api_base
    if needs_key and not api_key:
        msg = (
            f"\n  No LM configured (provider={provider!r} needs a key).\n"
            "\n"
            "  Pick one:\n"
            "    a) fully local (no key):  echo 'LM_MODEL=ollama/qwen3:35b' >> .env\n"
            "                              (requires Ollama running; see ollama.com)\n"
            "    b) anthropic:             echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env\n"
            "    c) any litellm provider:  see https://docs.litellm.ai/docs/providers\n"
            "\n"
            "  Then rerun.\n"
        )
        raise SystemExit(msg)

    lm_kwargs: dict = dict(
        max_tokens=int(os.environ.get("LM_MAX_TOKENS", "16384")),
        temperature=float(os.environ.get("LM_TEMPERATURE", "0.3")),
        num_retries=5,
    )
    if api_key:
        lm_kwargs["api_key"] = api_key
    if api_base:
        lm_kwargs["api_base"] = api_base

    lm = dspy.LM(model, **lm_kwargs)
    dspy.configure(lm=lm)


# ── The research task signature ────────────────────────────────────────────


class ResearchTask(dspy.Signature):
    """Answer a research question by searching the web and arXiv. Produce a
    grounded synthesis with explicit, verifiable citations.

    GROUNDING RULES — these are non-negotiable, every prior failure has
    been a violation of one of them:

    1. CITATIONS MUST BE REAL. Every arXiv ID you cite must come from an
       actual tool result you saw in THIS session — not from training-data
       recall, not from inference, not "this paper probably exists." If
       you cannot point to a specific arxiv_search or web_search result
       containing the ID, do not cite it. Fabricated arXiv IDs are the
       single most common failure mode and they are unacceptable.

    2. ANCHOR EACH CITATION. For every paper you put in a table or rely
       on for a non-trivial claim, you must have seen its title +
       abstract (or repo description) in a tool result. When in doubt,
       quote one specific phrase from the abstract that justifies the
       inclusion. This is the cheapest way to catch your own hallucinations.

    3. NEGATIVE RESULTS REQUIRE METHODOLOGY. If you conclude "no work
       exists at the intersection of X and Y" or "this is an open
       research gap," you must FIRST try at least 3–5 distinct query
       phrasings covering obvious synonyms and adjacent terms, and you
       must list those queries in your synthesis so the reader can
       judge how thorough the negative result is. A negative result
       without documented search effort is a guess, not a finding.

    4. PREFER PRIMARY SOURCES. Papers, official repos, and primary
       documentation beat secondary summaries, blog posts, or vendor
       marketing pages.

    5. UNKNOWN IS ACCEPTABLE. If you cannot verify a cell from a
       retrieved source, write UNKNOWN. Never fabricate a row, cell,
       citation, author name, or year. UNKNOWN is honest; a fabricated
       citation is not.

    6. INLINE CITATIONS use the form [arXiv:2402.16823] or [owner/repo].
    """

    current_date: str = dspy.InputField(
        desc="Today's date in YYYY-MM-DD format. Use this when assessing whether arXiv IDs or publication years are plausible."
    )
    question: str = dspy.InputField(
        desc="The research question to answer."
    )
    synthesis: str = dspy.OutputField(
        desc=(
            "A grounded answer to the question. For comparative / survey / "
            "design-space tasks, use Markdown tables with consistent columns "
            "across rows. For explanatory tasks, use 3-6 paragraphs of prose. "
            "For every row in a comparison table, you must have actually seen "
            "the cited paper's title and abstract (or repo description) in a "
            "tool result during this session — if you have not, omit the row "
            "or write UNKNOWN. When the conclusion is that an area is empty "
            "or sparse, include a short 'searches tried' note listing the "
            "specific queries you ran before reaching that conclusion, so the "
            "reader can judge thoroughness. Cite every non-trivial claim "
            "inline with [arXiv:id] or [owner/repo]. Never fabricate a row, "
            "cell, citation, or year — UNKNOWN is always preferable to a "
            "made-up source."
        )
    )
    sources: list[str] = dspy.OutputField(
        desc=(
            "A flat list of every URL or arXiv id cited in the synthesis, "
            "in the order they appear."
        )
    )


# ── The agent ──────────────────────────────────────────────────────────────


def build_agent() -> dspy.Module:
    """Build the un-optimized research agent.

    Tools (check local first — self-sovereign):
      - local_search            : SQLite FTS5 over the world_knowledge archive

    Tools (discovery — no API keys):
      - web_search              : SearXNG (primary) + DDG fallback, fan-out mode
      - expanded_search         : LM-expanded multi-query + reranked (widest recall)
      - nitter_search           : Twitter/X via open-source Nitter frontend
      - arxiv_search            : arXiv API
      - semantic_scholar_search : Semantic Scholar — broader than arXiv, citations

    Tools (discovery — GITHUB_TOKEN optional):
      - github_search           : GitHub repo search

    Tools (deep-read — local extraction, writes to world_knowledge/):
      - fetch_url               : trafilatura → Jina fallback, paginated, cached
      - fetch_urls_parallel     : batch-fetch up to 8 URLs concurrently
      - arxiv_fetch_paper       : full-text arXiv paper (not just abstract)
      - extract_links           : outbound link map for one-hop follow-up

    Tools (verification):
      - verify_arxiv_citations  : HEAD-check arXiv IDs to catch fabrications

    Tools ALWAYS try local_search before web_search. Only go online if
    local archive has no matches (or they look stale).
    """
    max_iters = int(os.environ.get("MAX_ITERS", "28"))
    raw_tools = [
        local_search,
        web_search,
        expanded_search,
        nitter_search,
        arxiv_search,
        semantic_scholar_search,
        github_search,
        fetch_url,
        fetch_urls_parallel,
        arxiv_fetch_paper,
        extract_links,
        verify_arxiv_citations,
    ]
    # Wrap each tool so the CLI can show a live trace of what the agent
    # picks on each turn. Set RA_QUIET=1 to suppress. The library import
    # path is unaffected; users importing `build_agent` programmatically
    # still get plain-stderr tool calls unless they explicitly set the
    # env var.
    tools = [_trace_tool(t) for t in raw_tools]
    return dspy.ReAct(ResearchTask, tools=tools, max_iters=max_iters)
