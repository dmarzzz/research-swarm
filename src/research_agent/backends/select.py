"""Backend selection and diagnostics."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

from research_agent.backends.base import ResearchRunner
from research_agent.backends.codex import CodexConfig, CodexResearchRunner, codex_smoke_check


@dataclass(frozen=True, slots=True)
class BackendChoice:
    requested: str
    selected: str
    reason: str


async def choose_backend(
    requested: str | None,
    *,
    codex_config: CodexConfig | None = None,
) -> BackendChoice:
    requested = (requested or os.environ.get("RA_BACKEND", "auto")).lower()
    if requested not in ("auto", "codex", "dspy"):
        raise ValueError(f"Unknown backend {requested!r}. Expected auto, codex, or dspy.")

    if requested == "dspy":
        return BackendChoice(requested=requested, selected="dspy", reason="requested")
    if requested == "codex":
        return BackendChoice(requested=requested, selected="codex", reason="requested")

    dspy_ready, dspy_reason = dspy_config_status()
    if dspy_ready:
        return BackendChoice(
            requested=requested,
            selected="dspy",
            reason=f"DSPy configured ({dspy_reason})",
        )

    ok, message = await codex_smoke_check(codex_config)
    if ok:
        return BackendChoice(
            requested=requested,
            selected="codex",
            reason=f"DSPy not configured ({dspy_reason}); {message}",
        )
    return BackendChoice(
        requested=requested,
        selected="dspy",
        reason=f"DSPy not configured ({dspy_reason}); Codex unavailable ({message})",
    )


def build_runner(choice: BackendChoice, *, codex_config: CodexConfig | None = None) -> ResearchRunner:
    if choice.selected == "codex":
        return CodexResearchRunner(config=codex_config)
    if choice.selected == "dspy":
        from research_agent.backends.dspy import DspyResearchRunner

        return DspyResearchRunner()
    raise ValueError(f"Unsupported backend: {choice.selected}")


def choose_backend_sync(
    requested: str | None,
    *,
    codex_config: CodexConfig | None = None,
) -> BackendChoice:
    return asyncio.run(choose_backend(requested, codex_config=codex_config))


def dspy_config_status() -> tuple[bool, str]:
    """Return whether the original DSPy backend appears configured.

    This is intentionally a cheap env-var check, not a network/model smoke.
    Explicit ``--backend dspy`` still runs ``configure_lm()`` and surfaces
    its existing friendly errors.
    """
    model = os.environ.get("LM_MODEL")
    api_key = os.environ.get("LM_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    api_base = os.environ.get("LM_API_BASE")

    if not model:
        if os.environ.get("ANTHROPIC_API_KEY"):
            return True, "ANTHROPIC_API_KEY"
        return False, "set LM_MODEL or ANTHROPIC_API_KEY for DSPy"

    provider = model.split("/", 1)[0] if "/" in model else ""
    if provider in ("ollama", "ollama_chat"):
        return True, f"LM_MODEL={model}"
    if api_key:
        return True, f"LM_MODEL={model} with API key"
    if api_base and provider == "openai":
        return True, f"LM_MODEL={model} with LM_API_BASE"
    return False, f"LM_MODEL={model} needs LM_API_KEY or ANTHROPIC_API_KEY"
