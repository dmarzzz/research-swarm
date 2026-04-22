"""Run logging.

Every research agent run is saved to runs/YYYYMMDD-HHMMSS-{slug}.json
with the original question, the synthesis, the cited sources, and the
self-critique (if it ran). Accumulated runs are the labeled corpus for
future MIPROv2 compilation — don't delete them unless you're sure.

The runs/ directory is gitignored because run logs can contain
copy-pasted API keys, private queries, or other sensitive material.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any


_CRITIQUE_FIELDS = (
    "coverage_gaps",
    "likely_errors",
    "grounding_score",
    "suggested_prompt_tweak",
    "overall_verdict",
)


def _slug(text: str, max_len: int = 44) -> str:
    """Make a short filesystem-safe slug from a question."""
    s = re.sub(r"[^a-z0-9]+", "-", text.lower())[:max_len].strip("-")
    return s or "run"


def log_run(
    *,
    question: str,
    synthesis: str,
    sources: list[str],
    critique: Any | None = None,
    prompt_version: str = "v2",
    runs_dir: Path | str = "runs",
) -> Path:
    """Write a single run to disk as JSON. Returns the path written.

    Swallows nothing — if the disk is full or the path is unwritable, the
    caller sees the exception and decides what to do. The caller is
    expected to wrap this in try/except so a logging failure doesn't
    take down the CLI.
    """
    runs_dir = Path(runs_dir)
    runs_dir.mkdir(exist_ok=True)

    now = datetime.now()
    filename = f"{now:%Y%m%d-%H%M%S}-{_slug(question)}.json"
    path = runs_dir / filename

    critique_data: dict | None = None
    if critique is not None:
        critique_data = {
            field: getattr(critique, field, None) for field in _CRITIQUE_FIELDS
        }

    path.write_text(
        json.dumps(
            {
                "timestamp": now.isoformat(),
                "prompt_version": prompt_version,
                "question": question,
                "synthesis": synthesis,
                "sources": sources,
                "critique": critique_data,
            },
            indent=2,
            default=str,
        )
    )
    return path
