from __future__ import annotations

from genshin_lore_db.search_engine.terminal import llm_status, prepare_terminal_llm, status_line


def test_llm_status_reports_validation_fallback() -> None:
    assert (
        llm_status(
            {
                "enabled": True,
                "used": False,
                "ok": False,
                "error": {"type": "validation_failed"},
            }
        )
        == "fallback:validation_failed"
    )


def test_status_line_includes_route_intent_and_llm() -> None:
    line = status_line(
        {
            "intent": "reliquary_effect_lookup",
            "route": {"mode": "basic_lookup", "confidence": 0.82},
            "llm": {"enabled": True, "used": True, "ok": True},
        }
    )

    assert line == "[route=basic_lookup:0.82 | intent=reliquary_effect_lookup | llm=used]"


def test_prepare_terminal_llm_skips_startup_when_disabled(monkeypatch) -> None:
    def fail_ready(*_args, **_kwargs):
        raise AssertionError("ensure_local_llm_ready should not be called")

    monkeypatch.setattr("genshin_lore_db.search_engine.terminal.ensure_local_llm_ready", fail_ready)

    enabled, status = prepare_terminal_llm(use_llm=False, model="test-model", auto_start_llm=True)

    assert enabled is False
    assert status["status"] == "disabled"
    assert status["available"] is False


def test_prepare_terminal_llm_disables_llm_when_model_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "genshin_lore_db.search_engine.terminal.ensure_local_llm_ready",
        lambda *_args, **_kwargs: {
            "available": False,
            "status": "model_missing",
            "message": "Run: ollama pull qwen3:4b-instruct",
        },
    )

    enabled, status = prepare_terminal_llm(use_llm=True, model="qwen3:4b-instruct", auto_start_llm=True)

    assert enabled is False
    assert status["status"] == "model_missing"
