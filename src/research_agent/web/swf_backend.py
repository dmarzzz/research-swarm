"""SWF-node HTTP client — used when the agent is embedded in a host
that runs a swf-node sidecar (Shape Rotator OS being the canonical
case).

When `RA_BACKEND=swf-node`, all web traffic from the agent —
`web_search`, `fetch_url`, `fetch_urls_parallel` — routes through the
peer daemon at `SWF_NODE_URL` instead of going direct to DDG / public
URLs. The peer becomes the single ingest point:

  · it owns the on-disk archive write (`~/world_knowledge/web/...`)
  · it applies the user's privacy / share-scope policy
  · it gets to see the page → atlas growth happens automatically

The agent stays a thin client. The default path
(`RA_BACKEND=direct`, or unset) is unchanged — non-SROS users keep
DDG + trafilatura + Jina.

Env vars:
    RA_BACKEND=swf-node         enables this module (default: direct)
    SWF_NODE_URL=http://...     base URL of the local peer
    SWF_NODE_TOKEN=...          bearer token for /fetch* endpoints
    SWF_PUBLIC_EGRESS=1         allow swf-node to hit the public web
                                (default: 1 — the swarm exists to
                                research the public internet)
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request


def enabled() -> bool:
    return (os.environ.get("RA_BACKEND") or "direct").strip().lower() == "swf-node"


def _base() -> str:
    base = (os.environ.get("SWF_NODE_URL") or "").rstrip("/")
    if not base:
        raise RuntimeError(
            "RA_BACKEND=swf-node but SWF_NODE_URL is not set"
        )
    return base


def _token() -> str:
    return (os.environ.get("SWF_NODE_TOKEN") or "").strip()


def _confirm_egress() -> bool:
    raw = (os.environ.get("SWF_PUBLIC_EGRESS") or "1").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _post(path: str, payload: dict, *, timeout: int, need_token: bool = False) -> dict:
    base = _base()
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "research-swarm",
    }
    token = _token()
    if need_token and not token:
        raise RuntimeError(
            f"swf-node {path} requires bearer token; SWF_NODE_TOKEN is not set"
        )
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def web_search(query: str, n: int = 8, *, request_id: str | None = None) -> list[dict]:
    """POST /web_search. Returns the same provider-shaped result list
    the local DDG/SearXNG providers produce, so callers don't have to
    branch on backend."""
    payload: dict = {
        "q": query,
        "top_k": max(1, min(50, int(n))),
        "policy": "default",
        "caller": "research-swarm",
        "confirm_public_egress": _confirm_egress(),
    }
    if request_id:
        payload["request_id"] = request_id
    resp = _post("/web_search", payload, timeout=30)
    results = (resp.get("results") or [])[:n]
    out: list[dict] = []
    for r in results:
        url = r.get("canonical_url") or r.get("display_url") or ""
        out.append({
            "title": r.get("title") or "",
            "url": url,
            "snippet": r.get("snippet") or "",
            "_provider": "swf",
        })
    return out


def fetch_url(url: str, *, max_chars: int = 200000) -> str:
    """POST /fetch. Returns the cleaned content string (markdown).

    swf-node handles the trafilatura / Jina fallback internally and
    writes the page to the shared `~/world_knowledge/` archive, so we
    don't need to do either on the agent side.
    """
    resp = _post(
        "/fetch",
        {"url": url, "start_char": 0, "max_chars": max_chars},
        timeout=60,
        need_token=True,
    )
    return resp.get("content") or ""
