"""DSPy tool adapters.

Thin layer over `research_agent.web.*` plus bounded-API academic/code
sources (arXiv, Semantic Scholar, GitHub). All agent-facing tool
docstrings live here so we can tune them without touching the crawl
internals.

Self-sovereign principles (see DESIGN.md):
    - `web_search`, `nitter_search`, `fetch_url`, `fetch_urls_parallel`,
      `extract_links`, `local_search` all work with no keys (SearXNG /
      DDG / Nitter / trafilatura / local SQLite FTS5).
    - `github_search` reads optional `GITHUB_TOKEN` (explicit exception
      per principles — GitHub content is irreplaceable).
    - `semantic_scholar_search` / `arxiv_search` / `arxiv_fetch_paper`
      use public academic APIs (no keys required at our volume).

Round 3 adds (LM-powered, no extra API keys):
    - `expanded_search`  — LM query-expansion + parallel fan-out + rerank.
    - `verify_arxiv_citations`  — HEAD-check arXiv IDs to catch fabrications.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import arxiv

from research_agent.web.crawl import extract_links  # noqa: F401
from research_agent.web.fetch import fetch_url, fetch_urls_parallel  # noqa: F401
from research_agent.web.index import local_search, reindex_knowledge  # noqa: F401
from research_agent.web.providers import (  # noqa: F401
    _dedupe_by_url,
    _fmt_results,
    nitter_search,
    web_search,
)


_TRACE_DIR = Path(os.environ.get("RA_TRACE_DIR", "traces"))


def _trace(tool: str, args: dict, meta: dict | None = None) -> None:
    try:
        _TRACE_DIR.mkdir(parents=True, exist_ok=True)
        path = _TRACE_DIR / f"tools-{datetime.now():%Y%m%d}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "ts": datetime.now().isoformat(timespec="seconds"),
                        "tool": tool,
                        "args": args,
                        "meta": meta or {},
                    },
                    default=str,
                )
                + "\n"
            )
    except Exception:
        pass


def _log(msg: str) -> None:
    if os.environ.get("RA_VERBOSE"):
        print(f"[tools] {msg}", file=sys.stderr)


# ── GitHub ─────────────────────────────────────────────────────────────────


def github_search(query: str) -> str:
    """Search GitHub for repositories matching a query.

    Use this to find open-source projects, frameworks, libraries, and tools.
    Especially useful for:
    - Finding ACTIVE projects (recent pushes, many stars)
    - Finding ABANDONED projects (last push > 2 years ago, few stars)
    - Discovering implementations that have no associated paper
    - Checking if a claimed repo actually exists

    Reads `GITHUB_TOKEN` from the environment if set (raises the rate
    limit from 60 to 5000 req/hr).

    Args:
        query: Keywords to search GitHub repos. Short terms work best
            ("federated reinforcement learning privacy"). You can also
            use GitHub qualifiers like "topic:marl" or "language:python".

    Returns:
        Up to 8 repos with name, URL, description, stars, language,
        last push date, creation date, and topic tags.
    """
    url = (
        "https://api.github.com/search/repositories"
        f"?q={urllib.parse.quote(query)}"
        "&sort=updated&order=desc&per_page=8"
    )
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "research-agent web_search",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    items = data.get("items", [])
    if not items:
        return f"No GitHub repositories found for: {query}"

    blocks = []
    for repo in items:
        blocks.append(
            f"- {repo['full_name']}\n"
            f"  URL: {repo['html_url']}\n"
            f"  Description: {repo.get('description') or 'N/A'}\n"
            f"  Stars: {repo['stargazers_count']}  |  "
            f"Language: {repo.get('language') or 'N/A'}\n"
            f"  Last pushed: {repo.get('pushed_at', 'N/A')}  |  "
            f"Created: {repo['created_at']}\n"
            f"  Topics: {', '.join(repo.get('topics', [])) or 'none'}"
        )
    _trace("github_search", {"query": query}, {"hits": len(items)})
    return "\n\n".join(blocks)


# ── arXiv ──────────────────────────────────────────────────────────────────


def arxiv_search(query: str) -> str:
    """Search arXiv for academic papers.

    Use this for peer-reviewed research, preprints, paper authors, or
    specific results. Prefer `web_search` when the question is about
    docs, blog posts, or repos.

    Args:
        query: A natural-language query. Title keywords, author names, or
            technical terms work best.

    Returns:
        Up to 5 papers formatted as title, authors, date, arXiv id, abstract.
    """
    search = arxiv.Search(
        query=query,
        max_results=5,
        sort_by=arxiv.SortCriterion.Relevance,
    )
    client = arxiv.Client()
    papers = list(client.results(search))
    if not papers:
        return "No arXiv papers found for that query."

    formatted = []
    for p in papers:
        authors = ", ".join(a.name for a in p.authors[:3])
        if len(p.authors) > 3:
            authors += " et al."
        summary = p.summary.strip().replace("\n", " ")[:600]
        formatted.append(
            f"- {p.title}\n"
            f"  {authors} ({p.published.date().isoformat()}) · arXiv:{p.get_short_id()}\n"
            f"  {summary}"
        )
    _trace("arxiv_search", {"query": query}, {"hits": len(papers)})
    return "\n\n".join(formatted)


def arxiv_fetch_paper(arxiv_id: str, start_char: int = 0, max_chars: int = 16000) -> str:
    """Fetch the FULL TEXT of an arXiv paper (not just the abstract).

    Normalizes common ID formats ("2402.16823", "arXiv:2402.16823",
    "2402.16823v2"). Returns paginated markdown like `fetch_url`.

    Args:
        arxiv_id: The paper's arXiv ID.
        start_char: Offset for pagination.
        max_chars: Per-call truncation (default 16000).

    Returns:
        Paginated full text with a header showing offset/total/remaining.
    """
    m = re.search(r"(\d{4}\.\d{4,5})(v\d+)?", arxiv_id)
    if not m:
        return f"arxiv_fetch_paper: could not parse an ID from {arxiv_id!r}"
    clean_id = m.group(1) + (m.group(2) or "")
    url = f"https://arxiv.org/abs/{clean_id}"
    _trace(
        "arxiv_fetch_paper",
        {"arxiv_id": arxiv_id, "resolved": clean_id, "start_char": start_char, "max_chars": max_chars},
        {},
    )
    return fetch_url(url, start_char=start_char, max_chars=max_chars)


# ── Semantic Scholar ───────────────────────────────────────────────────────


def semantic_scholar_search(query: str) -> str:
    """Search Semantic Scholar for academic papers (broader than arXiv).

    Use when `arxiv_search` comes up empty or for conference-venue
    publications. Also returns citation counts which help triage
    influential vs niche papers.

    Reads `SEMANTIC_SCHOLAR_API_KEY` if set (raises rate limit). Works
    unauthenticated but throttled.

    Args:
        query: Natural-language query.

    Returns:
        Up to 8 papers with title, authors, year, venue, citation count,
        and abstract.
    """
    fields = "title,authors,year,venue,citationCount,abstract,url,openAccessPdf,externalIds"
    url = (
        "https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={urllib.parse.quote(query)}&limit=8&fields={fields}"
    )
    headers = {"User-Agent": "research-agent web_search"}
    key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if key:
        headers["x-api-key"] = key

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read())
    papers = data.get("data", [])
    if not papers:
        return f"No Semantic Scholar results for: {query}"

    blocks = []
    for p in papers:
        authors = ", ".join(a.get("name", "?") for a in (p.get("authors") or [])[:3])
        if len(p.get("authors") or []) > 3:
            authors += " et al."
        year = p.get("year", "?")
        venue = p.get("venue") or "unpublished"
        cites = p.get("citationCount", 0)
        url_ = p.get("url", "")
        arxiv_id = (p.get("externalIds") or {}).get("ArXiv")
        pdf = (p.get("openAccessPdf") or {}).get("url", "")
        abstract = (p.get("abstract") or "").strip().replace("\n", " ")[:500]
        extras = []
        if arxiv_id:
            extras.append(f"arXiv:{arxiv_id}")
        if pdf:
            extras.append(f"PDF: {pdf}")
        extra_line = (" · " + " · ".join(extras)) if extras else ""
        blocks.append(
            f"- {p.get('title', '(no title)')}\n"
            f"  {authors} ({year}) · {venue} · {cites} citations{extra_line}\n"
            f"  {url_}\n"
            f"  {abstract}"
        )
    _trace("semantic_scholar_search", {"query": query}, {"hits": len(papers)})
    return "\n\n".join(blocks)


# ── LM-powered: expanded_search ────────────────────────────────────────────


def _parse_result_blocks(text: str) -> list[dict]:
    """Parse the formatted output of `web_search` back into dicts."""
    lines = text.splitlines()
    while lines and lines[0].startswith("["):
        lines.pop(0)

    blocks: list[dict] = []
    current: dict | None = None
    mode = "title"
    for ln in lines:
        if ln.startswith("- "):
            if current:
                blocks.append(current)
            current = {"title": ln[2:].strip(), "url": "", "snippet": ""}
            mode = "url"
        elif not ln.strip():
            if current:
                blocks.append(current)
                current = None
        elif current is not None:
            stripped = ln.strip()
            if mode == "url":
                current["url"] = stripped
                mode = "snippet"
            else:
                current["snippet"] = (current["snippet"] + " " + stripped).strip()
    if current:
        blocks.append(current)
    return [b for b in blocks if b.get("url")]


def _fmt_block(b: dict) -> str:
    return f"- {b['title']}\n  {b['url']}\n  {b.get('snippet', '')}"


def expanded_search(question: str, top_k: int = 10) -> str:
    """LM-expanded, reranked web search (wider + sharper than `web_search`).

    Pipeline:
      1. Expand the question into ~5 concrete search queries covering
         synonyms, adjacent terms, and specific technical phrasings.
      2. Run all queries through `web_search` in parallel.
      3. Deduplicate by URL, then rerank with an LM judge (0-10 relevance).
      4. Return the top `top_k` results plus the queries tried.

    Costs 2 extra LM calls but surfaces 2-3x more relevant sources.

    Args:
        question: A research question (a sentence, not keywords).
        top_k: How many reranked results to return (default 10).

    Returns:
        Top-k results with relevance scores, plus the list of tried queries.
    """
    import dspy as _dspy

    class _ExpandQ(_dspy.Signature):
        """Expand a research question into 4-6 short, concrete search queries
        that cover synonyms, adjacent terms, and specific technical phrasings.
        Prefer 2-6 word queries. Do not include the original verbatim — the
        expansion's value is VARIETY."""

        question: str = _dspy.InputField()
        queries: list[str] = _dspy.OutputField(
            desc="4-6 short search strings (2-6 words each). Distinct from each other."
        )

    class _RerankR(_dspy.Signature):
        """Given a research question and a list of candidate search results
        (title + url + snippet), score each candidate's relevance to the
        question on a 0-10 integer scale. Be strict — most real pools have
        a long tail of 0-3 scores."""

        question: str = _dspy.InputField()
        candidates: list[str] = _dspy.InputField(
            desc="Candidate blocks, each '- title\\n  url\\n  snippet'."
        )
        scores: list[int] = _dspy.OutputField(
            desc="One integer 0-10 per candidate, in the SAME order as input."
        )

    try:
        expander = _dspy.ChainOfThought(_ExpandQ)
        exp = expander(question=question)
        queries = list(dict.fromkeys([q.strip() for q in (exp.queries or []) if q and q.strip()]))[:6]
    except Exception as exc:
        _log(f"expand failed: {exc}")
        queries = []
    if not queries:
        queries = [question]

    pool: list[dict] = []
    contributors: dict[str, int] = {}
    with ThreadPoolExecutor(max_workers=min(6, len(queries))) as pool_exec:
        futs = {pool_exec.submit(web_search, q): q for q in queries}
        for fut in as_completed(futs):
            q = futs[fut]
            try:
                raw = fut.result()
            except Exception as exc:
                _log(f"sub-query {q!r} failed: {exc}")
                continue
            parsed = _parse_result_blocks(raw)
            contributors[q] = len(parsed)
            pool.extend(parsed)

    pool = _dedupe_by_url(pool)
    if not pool:
        return (
            f"expanded_search: no results across {len(queries)} queries.\n"
            f"Tried: {queries}"
        )

    shortlist = pool[:24]
    try:
        judge = _dspy.ChainOfThought(_RerankR)
        blocks = [_fmt_block(b) for b in shortlist]
        verdict = judge(question=question, candidates=blocks)
        raw_scores = verdict.scores or []
        if len(raw_scores) < len(shortlist):
            raw_scores = raw_scores + [0] * (len(shortlist) - len(raw_scores))
        scored = [(int(s), b) for s, b in zip(raw_scores, shortlist)]
    except Exception as exc:
        _log(f"rerank failed: {exc}")
        scored = [(5, b) for b in shortlist]

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[: max(1, int(top_k))]

    _trace(
        "expanded_search",
        {"question": question, "queries": queries, "top_k": top_k},
        {"pool_size": len(pool), "contributors": contributors, "kept": len(top)},
    )

    header = (
        f"[expanded_search · {len(queries)} queries → {len(pool)} merged "
        f"→ top {len(top)} after rerank]\n"
        f"queries tried: {queries}\n"
    )
    body = "\n\n".join(f"[rerank={s}] {_fmt_block(b)}" for s, b in top)
    return header + "\n" + body


# ── Citation verification ──────────────────────────────────────────────────


def verify_arxiv_citations(text: str) -> str:
    """Check that every arXiv ID cited in a synthesis actually resolves.

    Fabricated arXiv IDs are the single most common failure mode. This
    tool HEAD-checks every ID against arxiv.org and flags 404s.

    Args:
        text: Any text containing candidate arXiv IDs like "2402.16823"
            or "arXiv:2402.16823".

    Returns:
        Report listing each unique ID with OK / MISSING / ERROR status.
    """
    ids = sorted(set(re.findall(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b", text or "")))
    if not ids:
        return "verify_arxiv_citations: no arXiv IDs found in text."

    def _check(aid: str) -> tuple[str, str]:
        url = f"https://arxiv.org/abs/{aid}"
        req = urllib.request.Request(
            url, method="HEAD", headers={"User-Agent": "research-agent web_search"}
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return aid, "OK" if resp.status == 200 else f"HTTP {resp.status}"
        except urllib.error.HTTPError as exc:
            return aid, "MISSING" if exc.code == 404 else f"HTTP {exc.code}"
        except Exception as exc:
            return aid, f"ERROR: {type(exc).__name__}"

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=min(8, len(ids))) as pool:
        for aid, status in pool.map(_check, ids):
            results[aid] = status

    ok = sum(1 for v in results.values() if v == "OK")
    missing = [k for k, v in results.items() if v == "MISSING"]
    errors = {k: v for k, v in results.items() if v not in ("OK", "MISSING")}

    lines = [
        f"[verify_arxiv_citations · {len(ids)} IDs · {ok} OK · "
        f"{len(missing)} MISSING · {len(errors)} errors]"
    ]
    for aid, status in sorted(results.items()):
        marker = "✓" if status == "OK" else ("✗" if status == "MISSING" else "?")
        lines.append(f"  {marker} arXiv:{aid}  {status}")
    return "\n".join(lines)
