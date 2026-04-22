"""Web search providers for the research swarm.

Self-sovereign by default: zero API keys required.

Providers:
  - DDG   — DuckDuckGo via the `ddgs` package. Always available, free,
            no key. Primary fallback.
  - SearXNG — optional. Set `SEARXNG_URL` to an instance you trust or
              self-host. If set, we query it in parallel with DDG and
              merge results by canonical URL.

Rejected as defaults: Tavily, Brave API, Exa, Google CSE, Kagi,
SerpAPI. Paid intermediaries over the public web create vendor lock-in
and undermine the self-sovereign goal.

Gates applied in `web_search`:
  1. Staleness auto-bypass if the query contains temporal markers
     ("latest", "today", year, etc.) so news-ish queries always hit
     the network.
  2. Exact-query cache: if we've run this exact query in the last
     RA_CACHE_TTL_SEARCH seconds and have >= RA_CACHE_HIT_MIN rows,
     return cached and skip the network entirely.
  3. Otherwise fan out to DDG + SearXNG (if configured), merge,
     cache for next time, return.

`nitter_search` is kept as a separate tool because its output shape is
different (tweet stream vs. web result list).
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from ddgs import DDGS


def _log(msg: str) -> None:
    if os.environ.get("RA_VERBOSE"):
        print(f"[providers] {msg}", file=sys.stderr)


def _http_get(url: str, headers: dict | None = None, timeout: int = 20) -> bytes:
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


# ── Providers ─────────────────────────────────────────────────────────────


def _provider_ddg(query: str, n: int = 8) -> list[dict]:
    results = DDGS().text(query, max_results=n) or []
    return [
        {
            "title": r.get("title"),
            "url": r.get("href") or r.get("url"),
            "snippet": r.get("body") or r.get("description"),
            "_provider": "ddg",
        }
        for r in results
    ]


def _provider_searxng(query: str, n: int = 8) -> list[dict]:
    """Optional. If `SEARXNG_URL` is set, query it via its JSON API."""
    base = os.environ.get("SEARXNG_URL", "").rstrip("/")
    if not base:
        return []
    url = f"{base}/search?q={urllib.parse.quote(query)}&format=json&safesearch=0"
    try:
        data = json.loads(_http_get(url, headers={"User-Agent": "research-swarm"}, timeout=12))
    except Exception as exc:
        _log(f"searxng {base} failed: {exc}")
        return []
    results = (data.get("results") or [])[:n]
    return [
        {
            "title": r.get("title"),
            "url": r.get("url"),
            "snippet": r.get("content"),
            "_provider": f"searxng:{base}",
        }
        for r in results
    ]


_PROVIDERS = [
    ("searxng", _provider_searxng),
    ("ddg", _provider_ddg),
]


def _fmt_results(results: list[dict]) -> str:
    if not results:
        return ""
    blocks = []
    for r in results:
        title = (r.get("title") or "(no title)").strip()
        url = (r.get("url") or "").strip()
        snippet = (r.get("snippet") or "").strip().replace("\n", " ")[:500]
        blocks.append(f"- {title}\n  {url}\n  {snippet}")
    return "\n\n".join(blocks)


def _dedupe_by_url(results: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for r in results:
        u = (r.get("url") or "").strip().rstrip("/")
        if not u or u in seen:
            continue
        seen.add(u)
        out.append(r)
    return out


# ── Staleness heuristic ───────────────────────────────────────────────────


_TEMPORAL_MARKERS = (
    "today", "yesterday", "this week", "this month",
    "latest", "recent", "recently", "current", "currently",
    "right now", "breaking", "just released", "as of",
)


def _query_is_time_sensitive(query: str) -> str | None:
    """Return the marker that tripped, or None. Case-insensitive,
    word-boundary for single-word markers.

    A 4-digit year within +/-1 of the current calendar year also counts:
    queries mentioning the current year are likely time-sensitive.
    """
    q = (query or "").lower()
    for marker in _TEMPORAL_MARKERS:
        if " " in marker:
            if marker in q:
                return marker
        else:
            if re.search(rf"\b{re.escape(marker)}\b", q):
                return marker
    from datetime import datetime as _dt

    year = _dt.now().year
    for y in (year - 1, year, year + 1):
        if re.search(rf"\b{y}\b", q):
            return str(y)
    return None


# ── web_search ────────────────────────────────────────────────────────────


def web_search(query: str, fresh: bool = False) -> str:
    """Search the live web, local-cache-first.

    Pipeline:
      1. Staleness: if the query contains time-sensitive markers, bypass
         the cache (freshness matters more than avoiding the network).
      2. Cache gate: if this exact query was run within the last 7 days
         and yielded >= RA_CACHE_HIT_MIN rows, return cached, skip
         network.
      3. Otherwise, fan out in parallel to SearXNG (if configured) +
         DDG, merge + dedupe by URL, cache for next time, return.

    Force-fresh: pass `fresh=True` or set `RA_BYPASS_CACHE=1`.

    Args:
        query: Short, specific natural-language query.
        fresh: If True, bypass the cache for this call only.

    Returns:
        Formatted blocks of `- title\\n  url\\n  snippet`, up to ~16
        results, with a header showing where they came from.
    """
    # ── 1. Staleness + cache gates ───────────────────────────────────────
    env_bypass = os.environ.get("RA_BYPASS_CACHE") in ("1", "true", "yes")
    temporal = None if (env_bypass or fresh) else _query_is_time_sensitive(query)
    if temporal:
        _log(f"cache bypass · time-sensitive marker {temporal!r} in query")
    bypass = env_bypass or fresh or bool(temporal)

    if not bypass:
        hit_min = int(os.environ.get("RA_CACHE_HIT_MIN", "3"))
        ttl_sec = int(os.environ.get("RA_CACHE_TTL_SEARCH", str(7 * 24 * 3600)))
        try:
            from research_agent.web.index import get_cached_results

            cached = get_cached_results(query, max_age_seconds=ttl_sec)
        except Exception as exc:
            _log(f"cache read failed: {exc}")
            cached = []
        if len(cached) >= hit_min:
            _log(f"cache HIT · {len(cached)} rows for {query!r}")
            header = (
                f"[web_search LOCAL CACHE · {len(cached)} rows · "
                f"seen {cached[0].get('seen_at', '?')[:10]} · "
                f"skip network (pass fresh=True to override)]\n"
            )
            return header + _fmt_results(cached[:16])
        _log(f"cache miss · {len(cached)} rows for {query!r} (need {hit_min})")

    # ── 2. Provider fan-out ──────────────────────────────────────────────
    merged: list[dict] = []
    counts: dict[str, int] = {}
    errors: dict[str, str] = {}

    def _call(item):
        name, fn = item
        try:
            return name, fn(query, n=8), None
        except Exception as exc:
            return name, [], f"{type(exc).__name__}: {exc}"

    with ThreadPoolExecutor(max_workers=len(_PROVIDERS)) as pool:
        for name, results, err in pool.map(_call, _PROVIDERS):
            if err:
                errors[name] = err
                continue
            if results:
                counts[name] = len(results)
                merged.extend(results)
    merged = _dedupe_by_url(merged)

    if not merged:
        if errors and not counts:
            raise RuntimeError(f"web_search: all providers failed. Errors: {errors}")
        return "No web results found for that query."

    # ── 3. Write-through to the cache ────────────────────────────────────
    try:
        from research_agent.web.index import record_search_results

        engines_tag = ",".join(k for k, v in counts.items() if v > 0)
        record_search_results(query=query, results=merged, engines=engines_tag)
    except Exception as exc:
        _log(f"cache write failed: {exc}")

    contrib = ", ".join(f"{k}:{v}" for k, v in sorted(counts.items()))
    header = f"[web_search NETWORK · {contrib} · merged={len(merged)}]\n"
    return header + _fmt_results(merged[:16])


# ── Nitter (Twitter/X via an open-source frontend) ─────────────────────────


def _nitter_candidates() -> list[str]:
    raw = os.environ.get("NITTER_URL")
    if raw:
        return [u.strip().rstrip("/") for u in raw.split(",") if u.strip()]
    # Public instances come and go. Self-hosting is the reliable answer.
    return [
        "https://nitter.net",
        "https://nitter.privacydev.net",
        "https://nitter.poast.org",
        "https://nitter.fdn.fr",
    ]


_UA = (
    "Mozilla/5.0 (research-swarm) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


def nitter_search(query: str, from_user: str = "") -> str:
    """Search Twitter/X via Nitter (open-source frontend, no API key).

    Use for real-time discourse on niche technical topics: protocol
    debates, reactions to releases, expert commentary. Twitter's own
    API is paid and gates this content; Nitter scrapes the web UI.

    Public Nitter instances are fragile (Twitter blocks them regularly).
    This rotates through a few and returns the first that works.
    Self-host per https://github.com/zedeus/nitter for reliability, and
    point `NITTER_URL` at your instance.

    Args:
        query: Search terms (hashtags, phrases, usernames).
        from_user: Optional — restrict to a handle (without @).

    Returns:
        Up to 10 tweet stubs: author, date, snippet, nitter permalink.
    """
    q = query.strip()
    if from_user:
        q = f"{q} (from:{from_user.lstrip('@')})".strip()
    if not q:
        return "nitter_search: empty query"

    last_err: str | None = None
    for base in _nitter_candidates():
        url = f"{base}/search?f=tweets&q={urllib.parse.quote(q)}"
        try:
            raw = _http_get(
                url,
                headers={
                    "User-Agent": _UA,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                timeout=15,
            ).decode("utf-8", errors="replace")
        except Exception as exc:
            last_err = f"{base}: {type(exc).__name__}: {exc}"
            _log(f"nitter {base} failed: {exc}")
            continue

        tweets = _parse_nitter(raw, base)
        if tweets:
            header = f"[nitter_search via {base} · {len(tweets)} tweets]\n"
            blocks = [header]
            for t in tweets[:10]:
                blocks.append(
                    f"- @{t['user']} · {t['date']}\n"
                    f"  {base}{t['permalink']}\n"
                    f"  {t['text']}"
                )
            return "\n\n".join(blocks)

    return (
        "nitter_search: all public Nitter mirrors failed (or returned no tweets). "
        "Set NITTER_URL to a working instance, or self-host per "
        "https://github.com/zedeus/nitter. "
        f"Last error: {last_err or 'unknown'}"
    )


def _parse_nitter(html: str, base: str) -> list[dict]:
    tweets: list[dict] = []
    items = re.findall(
        r'<div[^>]*class="[^"]*timeline-item[^"]*"[^>]*>(.*?)(?=<div[^>]*class="[^"]*timeline-item|$)',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for item in items:
        user_m = re.search(r'class="username"[^>]*>@?([A-Za-z0-9_]+)', item)
        date_m = re.search(r'class="tweet-date"[^>]*>\s*<a[^>]*title="([^"]+)"', item)
        link_m = re.search(r'class="tweet-link"[^>]*href="([^"]+)"', item)
        text_m = re.search(
            r'class="tweet-content[^"]*"[^>]*>(.*?)</div>',
            item,
            flags=re.DOTALL,
        )
        if not user_m or not link_m:
            continue
        text = ""
        if text_m:
            text = re.sub(r"<[^>]+>", " ", text_m.group(1))
            text = re.sub(r"\s+", " ", text).strip()[:400]
        tweets.append(
            {
                "user": user_m.group(1),
                "date": (date_m.group(1) if date_m else "")[:60],
                "permalink": link_m.group(1),
                "text": text or "(no text extracted)",
            }
        )
    return tweets
