"""Verifies RA_BACKEND=swf-node routes web_search + fetch through a
local swf-node HTTP endpoint instead of DDG / direct urllib.

Spins up a tiny stdlib http.server on a free port, points the agent
at it via SWF_NODE_URL, and asserts the request shape + response
plumbing for /web_search and /fetch.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest


class _Captured:
    """Records each request the fake swf-node received."""
    def __init__(self) -> None:
        self.calls: list[dict] = []


def _make_handler(captured: _Captured):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a, **k):  # silence default stderr noise
            return

        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            captured.calls.append({
                "path": self.path,
                "auth": self.headers.get("Authorization") or "",
                "body": payload,
            })
            if self.path == "/web_search":
                resp = {
                    "results": [
                        {
                            "canonical_url": "https://example.com/loopix",
                            "display_url": "example.com/loopix",
                            "title": "Loopix — mix network design",
                            "snippet": "low-latency anonymous comms ...",
                            "score": 0.97,
                            "rank": 0,
                        }
                    ],
                }
                data = json.dumps(resp).encode("utf-8")
            elif self.path == "/fetch":
                resp = {"content": "# Loopix\n\nFull text from swf-node."}
                data = json.dumps(resp).encode("utf-8")
            else:
                self.send_response(404)
                self.end_headers()
                return
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
    return Handler


@pytest.fixture
def fake_swf(monkeypatch):
    captured = _Captured()
    # Pick a free port.
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = HTTPServer(("127.0.0.1", port), _make_handler(captured))
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    monkeypatch.setenv("RA_BACKEND", "swf-node")
    monkeypatch.setenv("SWF_NODE_URL", f"http://127.0.0.1:{port}")
    monkeypatch.setenv("SWF_NODE_TOKEN", "test-token")
    try:
        yield captured
    finally:
        srv.shutdown()
        srv.server_close()


def test_web_search_routes_through_swf(fake_swf, monkeypatch):
    # Force-bypass the agent's local cache so the request actually goes
    # out (not strictly needed once the swf-node short-circuit runs
    # before the cache gate, but belt-and-suspenders).
    monkeypatch.setenv("RA_BYPASS_CACHE", "1")
    from research_agent.web.providers import web_search

    out = web_search("Loopix")
    assert "Loopix" in out
    assert "SWF-NODE" in out
    assert any(c["path"] == "/web_search" for c in fake_swf.calls)
    call = next(c for c in fake_swf.calls if c["path"] == "/web_search")
    assert call["body"]["q"] == "Loopix"
    assert call["body"]["confirm_public_egress"] is True
    assert call["body"]["caller"] == "research-swarm"


def test_fetch_routes_through_swf_with_bearer(fake_swf):
    from research_agent.web.fetch import _get_clean_text

    text, _title, extractor = _get_clean_text("https://example.com/loopix")
    assert "Loopix" in text
    assert extractor == "swf-node"
    call = next(c for c in fake_swf.calls if c["path"] == "/fetch")
    assert call["auth"] == "Bearer test-token"
    assert call["body"]["url"] == "https://example.com/loopix"


def test_fetch_requires_token(monkeypatch):
    monkeypatch.setenv("RA_BACKEND", "swf-node")
    monkeypatch.setenv("SWF_NODE_URL", "http://127.0.0.1:1")  # unused
    monkeypatch.delenv("SWF_NODE_TOKEN", raising=False)
    from research_agent.web import swf_backend

    with pytest.raises(RuntimeError, match="SWF_NODE_TOKEN"):
        swf_backend.fetch_url("https://example.com/x")


def test_backend_default_is_direct(monkeypatch):
    monkeypatch.delenv("RA_BACKEND", raising=False)
    from research_agent.web import swf_backend

    assert swf_backend.enabled() is False
