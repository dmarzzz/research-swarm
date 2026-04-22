"""SQLite FTS5 index of everything in world_knowledge/web/.

The agent should check here before going online. Every `fetch_url` call
that writes to world_knowledge/ also updates this index.

Database path: `<knowledge_root>/index.db`.

Public surface:
    - index_page(url, title, content, fetched_at)  — upsert one page
    - local_search(query, limit=8)  — FTS5 search, returns snippets
    - reindex_knowledge()  — rebuild from scratch from world_knowledge/web/
"""

from __future__ import annotations

import os
import sqlite3
import sys
import threading
from pathlib import Path

from research_agent.web.knowledge import knowledge_root
from research_agent.web.canonical import canonical_url_safe


_LOCK = threading.Lock()


def _db_path() -> Path:
    root = knowledge_root()
    return root / "index.db"


def _conn() -> sqlite3.Connection:
    # check_same_thread=False + our own lock so we can use this from ReAct's
    # thread pool. SQLite is fast enough on a single-writer index.
    conn = sqlite3.connect(_db_path(), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode is mandatory: it lets concurrent readers (the searxng engine
    # adapter in swf/local_index.py) see committed writes without blocking.
    # Idempotent; safe to set on every connection.
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
    except sqlite3.DatabaseError:
        # Fresh DB may need the table created first; fall through.
        pass
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS pages USING fts5(
            url UNINDEXED,
            title,
            content,
            fetched_at UNINDEXED,
            tokenize = 'porter unicode61'
        )
        """
    )
    # search_results caches every URL+title+snippet we've ever seen from
    # ANY engine for ANY query, not just pages we actually fetched. This
    # is what makes "same query twice is local" work even for URLs the
    # agent never picked to fetch_url. Content-searchable via FTS5 on
    # title+snippet; also queryable by exact query_hash for cache-hit
    # detection in the agent's web_search gate.
    conn.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS search_results USING fts5(
            query_hash UNINDEXED,
            query UNINDEXED,
            url UNINDEXED,
            title,
            snippet,
            engines UNINDEXED,
            seen_at UNINDEXED,
            tokenize = 'porter unicode61'
        )
        """
    )
    # Second attempt after tables exist, in case the fresh-DB path took
    # the exception branch above.
    try:
        conn.execute("PRAGMA journal_mode=WAL")
    except sqlite3.DatabaseError:
        pass
    return conn


def index_page(*, url: str, title: str, content: str, fetched_at: str) -> None:
    """Upsert a page into the FTS index. Best-effort; never raises.

    URL is canonicalized on the way in so the searxng engine adapter's
    exact-string dedup against public-engine results will work. If the
    URL fails canonicalization we skip the row (invalid URLs in, no
    record out).
    """
    if not url or not content:
        return
    canon = canonical_url_safe(url)
    if canon is None:
        print(f"[index] skipped invalid url: {url!r}", file=sys.stderr)
        return
    try:
        with _LOCK:
            conn = _conn()
            try:
                # Delete any prior entry for this URL, then insert fresh.
                conn.execute("DELETE FROM pages WHERE url = ?", (canon,))
                conn.execute(
                    "INSERT INTO pages (url, title, content, fetched_at) VALUES (?, ?, ?, ?)",
                    (canon, title or "", content, fetched_at or ""),
                )
                conn.commit()
            finally:
                conn.close()
    except Exception as exc:
        print(f"[index] skipped {url}: {exc}", file=sys.stderr)


# ── Ship 0.1: query + result-list cache ────────────────────────────────────


def _query_hash(query: str) -> str:
    """Stable hash of a query string. Case-insensitive, whitespace-normalized."""
    import hashlib as _h

    normalized = " ".join((query or "").lower().split())
    return _h.sha1(normalized.encode("utf-8")).hexdigest()[:16]


def record_search_results(
    *, query: str, results: list[dict], engines: str = "", now_iso: str | None = None
) -> int:
    """Persist a searxng/web_search result list into the `search_results`
    cache. Each result dict should have keys: `url`, `title`, `snippet`
    (snippet may also be called `content`/`body`/`description`; we try
    common aliases). Returns the number of rows actually written.

    Idempotent per (query_hash, url): re-running the same query replaces
    prior rows for that query (staleness via `seen_at`).
    """
    if not query or not results:
        return 0
    from datetime import datetime as _dt

    qh = _query_hash(query)
    stamp = now_iso or _dt.now().isoformat(timespec="seconds")

    rows: list[tuple] = []
    for r in results:
        url = r.get("url") or r.get("href") or ""
        canon = canonical_url_safe(url)
        if not canon:
            continue
        title = (r.get("title") or "").strip()
        snippet = (
            r.get("snippet")
            or r.get("content")
            or r.get("body")
            or r.get("description")
            or ""
        ).strip().replace("\n", " ")[:800]
        rows.append((qh, query, canon, title, snippet, engines, stamp))

    if not rows:
        return 0

    try:
        with _LOCK:
            conn = _conn()
            try:
                # Fresh per-query snapshot: drop prior rows for this query,
                # then insert the new set. Keeps the cache stable-sized and
                # reflects the most recent observation.
                conn.execute(
                    "DELETE FROM search_results WHERE query_hash = ?", (qh,)
                )
                conn.executemany(
                    "INSERT INTO search_results "
                    "(query_hash, query, url, title, snippet, engines, seen_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    rows,
                )
                conn.commit()
            finally:
                conn.close()
    except Exception as exc:
        print(f"[index] record_search_results failed: {exc}", file=sys.stderr)
        return 0
    return len(rows)


def get_cached_results(
    query: str, max_age_seconds: int = 7 * 24 * 3600
) -> list[dict]:
    """Return cached search-results rows for this exact query if any were
    seen within the last `max_age_seconds`. Empty list if miss or stale.

    Each row: {url, title, snippet, seen_at, engines}. URLs are canonical.
    """
    if not query:
        return []

    qh = _query_hash(query)
    try:
        with _LOCK:
            conn = _conn()
            try:
                rows = conn.execute(
                    "SELECT url, title, snippet, seen_at, engines "
                    "  FROM search_results "
                    " WHERE query_hash = ? "
                    " ORDER BY seen_at DESC",
                    (qh,),
                ).fetchall()
            finally:
                conn.close()
    except Exception as exc:
        print(f"[index] get_cached_results failed: {exc}", file=sys.stderr)
        return []

    if not rows:
        return []

    # Freshness filter: drop rows older than max_age_seconds.
    from datetime import datetime as _dt

    fresh: list[dict] = []
    now = _dt.now()
    for r in rows:
        seen_at = r["seen_at"] or ""
        try:
            age = (now - _dt.fromisoformat(seen_at)).total_seconds()
        except Exception:
            age = 0
        if age <= max_age_seconds:
            fresh.append(
                {
                    "url": r["url"],
                    "title": r["title"],
                    "snippet": r["snippet"],
                    "seen_at": seen_at,
                    "engines": r["engines"],
                }
            )
    return fresh


def _fts_search_table(
    conn: sqlite3.Connection,
    table: str,
    match_col_index: int,
    query: str,
    limit: int,
    extra_cols: str,
) -> list[sqlite3.Row]:
    """Run one FTS5 MATCH against a specific table with a quoted-phrase
    fallback on syntax error. `match_col_index` is the column index of
    the matching content column for the `snippet()` aux function."""
    sql = (
        f"SELECT url, title, {extra_cols}, "
        f"       snippet({table}, {match_col_index}, '«', '»', '…', 20) AS snip "
        f"  FROM {table} "
        f" WHERE {table} MATCH ? "
        f" ORDER BY rank "
        f" LIMIT ?"
    )
    try:
        return conn.execute(sql, (query, limit)).fetchall()
    except sqlite3.OperationalError as exc:
        if "syntax error" in str(exc).lower():
            return conn.execute(sql, (f'"{query}"', limit)).fetchall()
        raise


def local_search(query: str, limit: int = 8) -> str:
    """Search the local world_knowledge archive.

    Unions two FTS5 tables:
      - `pages`: content the agent actually fetched (full markdown).
      - `search_results`: URLs seen in prior search results (title + snippet),
         even if never fetched in full.

    Same-URL hits from `pages` take precedence (full content beats snippet).

    Args:
        query: FTS5 query string. Supports phrases, booleans, prefix.
        limit: Max results to return (default 8).

    Returns:
        Header + per-result block. Each block marked [page] or [cache]
        so the caller can tell full content from snippet-only entries.
    """
    if not query or not query.strip():
        return "local_search: empty query"

    capped = max(1, min(limit, 50))
    pages_rows: list[sqlite3.Row] = []
    cache_rows: list[sqlite3.Row] = []

    try:
        with _LOCK:
            conn = _conn()
            try:
                pages_rows = _fts_search_table(
                    conn, "pages", match_col_index=2,
                    query=query, limit=capped, extra_cols="fetched_at",
                )
                cache_rows = _fts_search_table(
                    conn, "search_results", match_col_index=4,
                    query=query, limit=capped, extra_cols="seen_at, engines",
                )
            finally:
                conn.close()
    except Exception as exc:
        return f"local_search: {exc}"

    page_urls = {r["url"] for r in pages_rows}
    if not pages_rows and not cache_rows:
        return (
            f"local_search: no local matches for {query!r} — archive may not "
            "cover this yet; try web_search."
        )

    blocks: list[str] = []
    for r in pages_rows[:capped]:
        title = (r["title"] or "(no title)").strip().splitlines()[0][:120]
        date = (r["fetched_at"] or "")[:10]
        snip = (r["snip"] or "").replace("\n", " ").strip()[:300]
        blocks.append(f"- [page] {title}\n  {r['url']}\n  fetched {date}\n  {snip}")

    cache_remaining = [r for r in cache_rows if r["url"] not in page_urls]
    for r in cache_remaining[: max(0, capped - len(pages_rows))]:
        title = (r["title"] or "(no title)").strip().splitlines()[0][:120]
        date = (r["seen_at"] or "")[:10]
        snip = (r["snip"] or "").replace("\n", " ").strip()[:300]
        engines = r["engines"] or ""
        engines_tag = f" · via {engines}" if engines else ""
        blocks.append(f"- [cache] {title}\n  {r['url']}\n  seen {date}{engines_tag}\n  {snip}")

    header = (
        f"[local_search · {len(pages_rows)} page-hit(s) + "
        f"{len(cache_remaining)} cache-hit(s) in world_knowledge]"
    )
    return header + "\n\n" + "\n\n".join(blocks)


def reindex_knowledge() -> str:
    """Rebuild the FTS index from everything on disk in world_knowledge/web/.

    Idempotent. Useful after manual edits, after restoring from backup,
    or after upgrading the schema.
    """
    root = knowledge_root() / "web"
    count = 0
    errors = 0

    with _LOCK:
        conn = _conn()
        try:
            conn.execute("DELETE FROM pages")
            for md_path in root.rglob("*.md"):
                try:
                    text = md_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    errors += 1
                    continue
                url, title, fetched_at, body = _parse_frontmatter(text)
                if not url:
                    continue
                canon = canonical_url_safe(url) or url
                conn.execute(
                    "INSERT INTO pages (url, title, content, fetched_at) VALUES (?, ?, ?, ?)",
                    (canon, title or md_path.stem, body, fetched_at or ""),
                )
                count += 1
            conn.commit()
        finally:
            conn.close()

    return f"reindex_knowledge: indexed {count} page(s), {errors} read error(s). DB: {_db_path()}"


def _parse_frontmatter(text: str) -> tuple[str, str, str, str]:
    """Very small YAML-ish frontmatter parser. Returns (url, title, fetched_at, body)."""
    if not text.startswith("---\n"):
        return "", "", "", text
    end = text.find("\n---\n", 4)
    if end == -1:
        return "", "", "", text
    header_block = text[4:end]
    body = text[end + 5 :]
    kv: dict[str, str] = {}
    for line in header_block.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        kv[k.strip()] = v.strip()
    return kv.get("url", ""), kv.get("title", ""), kv.get("fetched_at", ""), body
