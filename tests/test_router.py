from __future__ import annotations

from genshin_lore_db.search_engine.router import route_query


def test_basic_info_query_routes_to_basic_lookup() -> None:
    decision = route_query("푸리나 기본정보")

    assert decision.mode == "basic_lookup"
    assert "game_info:기본정보" in decision.signals


def test_plain_info_query_routes_to_basic_lookup() -> None:
    decision = route_query("안개를 가르는 회광 정보")

    assert decision.mode == "basic_lookup"
    assert "game_info:정보" in decision.signals


def test_greeting_routes_to_chitchat_guard() -> None:
    decision = route_query("안녕하세요")

    assert decision.mode == "chitchat"
    assert "guard:greeting" in decision.signals


def test_relation_signal_stays_analysis() -> None:
    decision = route_query("천리와 셀레스티아 관계")

    assert decision.mode == "analysis"
