from __future__ import annotations

from genshin_lore_db.search_engine.terminal import llm_status, status_line


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
