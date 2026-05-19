import research_agent.main as main_mod


def test_backend_flag_overrides_env_before_run(monkeypatch) -> None:
    captured = {}

    async def fake_amain(args, question: str) -> int:
        captured["backend"] = args.backend
        captured["question"] = question
        return 0

    monkeypatch.setenv("RA_BACKEND", "codex")
    monkeypatch.setattr(main_mod, "_amain", fake_amain)

    assert main_mod.main(["--backend", "dspy", "hello"]) == 0
    assert captured == {"backend": "dspy", "question": "hello"}


def test_missing_backend_flag_defers_to_env_resolution(monkeypatch) -> None:
    captured = {}

    async def fake_amain(args, question: str) -> int:
        captured["backend"] = args.backend
        captured["question"] = question
        return 0

    monkeypatch.setenv("RA_BACKEND", "dspy")
    monkeypatch.setattr(main_mod, "_amain", fake_amain)

    assert main_mod.main(["hello"]) == 0
    assert captured == {"backend": None, "question": "hello"}
