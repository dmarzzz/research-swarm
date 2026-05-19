import asyncio

from research_agent.backends.select import choose_backend, dspy_config_status


DSPY_ENV = (
    "LM_MODEL",
    "LM_API_KEY",
    "LM_API_BASE",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_MODEL",
)


def clear_dspy_env(monkeypatch) -> None:
    for name in DSPY_ENV:
        monkeypatch.delenv(name, raising=False)


def test_auto_selects_dspy_when_dspy_is_configured(monkeypatch) -> None:
    monkeypatch.setenv("LM_MODEL", "ollama/qwen3:35b")

    async def fail_if_called(config=None):
        raise AssertionError("Codex smoke should not run when DSPy is configured")

    monkeypatch.setattr("research_agent.backends.select.codex_smoke_check", fail_if_called)

    choice = asyncio.run(choose_backend("auto"))

    assert choice.selected == "dspy"
    assert "DSPy configured" in choice.reason


def test_auto_selects_codex_when_dspy_unconfigured_and_smoke_passes(monkeypatch) -> None:
    clear_dspy_env(monkeypatch)

    async def ok(config=None):
        return True, "passed"

    monkeypatch.setattr("research_agent.backends.select.codex_smoke_check", ok)

    choice = asyncio.run(choose_backend("auto"))

    assert choice.selected == "codex"
    assert "DSPy not configured" in choice.reason
    assert "passed" in choice.reason


def test_auto_returns_dspy_when_neither_backend_is_ready(monkeypatch) -> None:
    clear_dspy_env(monkeypatch)

    async def nope(config=None):
        return False, "missing"

    monkeypatch.setattr("research_agent.backends.select.codex_smoke_check", nope)

    choice = asyncio.run(choose_backend("auto"))

    assert choice.selected == "dspy"
    assert "missing" in choice.reason


def test_explicit_backend_skips_smoke(monkeypatch) -> None:
    async def fail_if_called(config=None):
        raise AssertionError("smoke should not run")

    monkeypatch.setattr("research_agent.backends.select.codex_smoke_check", fail_if_called)

    assert asyncio.run(choose_backend("dspy")).selected == "dspy"
    assert asyncio.run(choose_backend("codex")).selected == "codex"


def test_env_backend_is_used_when_request_is_omitted(monkeypatch) -> None:
    monkeypatch.setenv("RA_BACKEND", "codex")

    choice = asyncio.run(choose_backend(None))

    assert choice.requested == "codex"
    assert choice.selected == "codex"


def test_explicit_backend_overrides_env_backend(monkeypatch) -> None:
    monkeypatch.setenv("RA_BACKEND", "codex")

    choice = asyncio.run(choose_backend("dspy"))

    assert choice.requested == "dspy"
    assert choice.selected == "dspy"


def test_dspy_config_status_accepts_api_base_without_key(monkeypatch) -> None:
    clear_dspy_env(monkeypatch)
    monkeypatch.setenv("LM_MODEL", "openai/my-local")
    monkeypatch.setenv("LM_API_BASE", "http://localhost:8000/v1")

    ready, reason = dspy_config_status()

    assert ready is True
    assert "LM_API_BASE" in reason
