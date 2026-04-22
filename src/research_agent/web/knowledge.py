"""Write-through to the world_knowledge/ folder.

Every successful fetch lands here as a markdown file with YAML frontmatter,
under `~/world_knowledge/web/<domain>/<yyyy-mm-dd>-<slug>.md`. This is the
accumulating local archive — the longer the agent runs, the richer it gets.

Set `RA_WORLD_KNOWLEDGE_DIR` to override the root. Set `RA_WORLD_KNOWLEDGE=0`
to disable write-through entirely (for sandboxed / test runs).
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from research_agent.web.canonical import canonical_url_safe


def knowledge_root() -> Path:
    """Return the configured world_knowledge root, creating it if needed.

    Default: `~/world_knowledge/`. Override with `RA_WORLD_KNOWLEDGE_DIR`.
    """
    root = Path(os.environ.get("RA_WORLD_KNOWLEDGE_DIR", Path.home() / "world_knowledge"))
    (root / "web").mkdir(parents=True, exist_ok=True)
    return root


def _enabled() -> bool:
    return os.environ.get("RA_WORLD_KNOWLEDGE", "1") not in ("0", "false", "no")


def _slug(text: str, max_len: int = 64) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (s or "page")[:max_len]


def _infer_title(text: str) -> str | None:
    """Best-effort pull of a title line from extracted markdown."""
    if not text:
        return None
    for line in text.splitlines()[:30]:
        line = line.strip()
        if not line:
            continue
        if line.lower().startswith("title:"):
            return line.split(":", 1)[1].strip()
        if line.startswith("# "):
            return line[2:].strip()
    return None


def world_path_for(url: str, title: str | None = None) -> Path:
    """Compute the on-disk path for a URL (without writing).

    Shape: <root>/web/<domain>/<yyyy-mm-dd>-<slug>.md
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower() or "unknown"
    today = datetime.now().strftime("%Y-%m-%d")
    path_slug = _slug(parsed.path) or "root"
    if title:
        slug = _slug(title)[:48] + "-" + path_slug[:20]
    else:
        slug = path_slug
    return knowledge_root() / "web" / domain / f"{today}-{slug}.md"


def world_write(url: str, text: str, *, extractor: str, title: str | None = None) -> Path | None:
    """Write a fetched page to world_knowledge/. Returns the path, or None if disabled.

    Idempotent on content: if a file for this URL already exists with the
    same content hash, we don't rewrite it (preserves fetched_at of the
    first capture). If content differs, we write a new dated file, so
    revision history is naturally preserved.

    URL is canonicalized (see `research_agent.web.canonical`) so downstream
    consumers get deterministic, dedup-friendly keys.
    """
    if not _enabled() or not text:
        return None

    canon = canonical_url_safe(url) or url
    title = title or _infer_title(text) or urlparse(canon).path or canon
    path = world_path_for(canon, title)
    path.parent.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha1(text.encode("utf-8")).hexdigest()

    # Avoid rewriting an identical snapshot.
    if path.exists():
        existing = path.read_text(encoding="utf-8", errors="replace")
        if f"content_hash: sha1:{content_hash}" in existing:
            return path

    body = f"""---
url: {canon}
title: {title}
fetched_at: {datetime.now().isoformat(timespec="seconds")}
content_hash: sha1:{content_hash}
extractor: {extractor}
---

{text}
"""
    try:
        path.write_text(body, encoding="utf-8")
    except Exception as exc:
        print(f"[knowledge] write failed for {canon}: {exc}", file=sys.stderr)
        return None

    # Best-effort index update.
    try:
        from research_agent.web.index import index_page

        index_page(url=canon, title=title, content=text, fetched_at=datetime.now().isoformat())
    except Exception as exc:
        print(f"[knowledge] index update failed for {canon}: {exc}", file=sys.stderr)

    return path
