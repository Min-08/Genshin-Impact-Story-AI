from __future__ import annotations

from pathlib import Path

from genshin_lore_db.search_engine.conversation import ConversationState
from genshin_lore_db.search_engine.qa import answer_question
from genshin_lore_db.search_engine.query_understanding import understand_query


ROOT = Path(".")
DB = ROOT / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"


def selected(result: dict) -> dict:
    return result["selected_candidate"]


def test_query_understanding_greeting_uses_chitchat_guard() -> None:
    for query in ["안녕", "hi"]:
        result = understand_query(ROOT, query, db_path=DB, use_llm=False)
        item = selected(result)

        assert item["id"] == "guard:chitchat", query
        assert item["route_candidate"] == "chitchat"
        assert item["match_strength"] == "strong"
        assert "guard:greeting" in item["match_reasons"]


def test_query_understanding_selects_supported_entities() -> None:
    cases = [
        ("푸리나 기본정보", "avatar", "project_amber:avatar:10000089"),
        ("절연의 기치 효과", "reliquary", "project_amber:reliquary:15020"),
        ("타오르는 천 개의 태양 제련별 수치", "weapon", "project_amber:weapon:12514"),
        ("천 개의 태양 제련별 수치", "weapon", "project_amber:weapon:12514"),
    ]

    for query, content_type, canonical_id in cases:
        result = understand_query(ROOT, query, db_path=DB, use_llm=False)
        item = selected(result)

        assert item["kind"] == "supported_entity", query
        assert item["match_strength"] == "strong", query
        assert item["route_candidate"] == "basic_lookup", query
        assert item["content_type"] == content_type
        assert item["canonical_id"] == canonical_id
        assert item["match_reasons"]


def test_query_understanding_selects_lore_concepts_over_weak_supported_overlap() -> None:
    for query in [
        "천리",
        "천리가 뭐야",
        "천리 알려줘",
        "파네스",
        "세계수",
        "니벨룽겐",
        "운명의 베틀",
        "강림자",
        "셀레스티아",
        "심연",
        "켄리아",
        "카엔리아",
        "금지된 지식",
        "달의 세 자매",
    ]:
        result = understand_query(ROOT, query, db_path=DB, use_llm=False)
        item = selected(result)

        assert item["kind"] == "lore_concept", query
        assert item["match_strength"] == "strong", query
        assert item["route_candidate"] == "analysis", query
        assert result["selected_meaning"]["supported_for_current_writer"] is False
        assert item["match_reasons"]


def test_query_understanding_story_scope_and_explicit_topic_rejects_context() -> None:
    state = ConversationState(
        active_entity={
            "name": "안개를 가르는 회광",
            "content_type": "weapon",
            "canonical_id": "project_amber:weapon:11509",
            "item_id": "11509",
        }
    )

    result = understand_query(ROOT, "수메르 스토리 요약해줘", db_path=DB, conversation_state=state, use_llm=False)
    item = selected(result)

    assert item["kind"] == "region_or_story_scope"
    assert item["route_candidate"] == "summary"
    assert item["context_used"] is False
    assert result["conversation_context"]["explicit_topic_detected"] is True
    assert result["conversation_context"]["rejected_reason"] == "explicit_topic"


def test_query_understanding_low_information_followup_uses_context() -> None:
    first = answer_question(ROOT, "안개를 가르는 회광 알려줘", use_llm=False)
    state = ConversationState()
    state.update_from_result(first)

    result = understand_query(ROOT, "제련 효과는?", db_path=DB, conversation_state=state, use_llm=False)
    item = selected(result)

    assert item["kind"] == "followup_request"
    assert item["route_candidate"] == "basic_lookup"
    assert item["context_used"] is True
    assert item["canonical_id"] == "project_amber:weapon:11509"


def test_query_understanding_llm_enabled_followup_gate_uses_context() -> None:
    first = answer_question(ROOT, "푸리나 기본정보", use_llm=False)
    state = ConversationState()
    state.update_from_result(first)

    result = understand_query(ROOT, "스토리 요약해줘", db_path=DB, conversation_state=state, use_llm=True)
    item = selected(result)

    assert item["kind"] == "followup_request"
    assert item["route_candidate"] == "summary"
    assert item["context_used"] is True
    assert item["canonical_id"] == "project_amber:avatar:10000089"


def test_query_understanding_source_followup_requires_source_context() -> None:
    no_context = understand_query(ROOT, "근거는?", db_path=DB, use_llm=False)
    assert selected(no_context)["kind"] == "source_or_evidence_request"
    assert selected(no_context)["route_candidate"] == "unsupported"
    assert "missing_prior_source_context" in selected(no_context)["risk_flags"]

    state = ConversationState()
    state.update_from_result(answer_question(ROOT, "푸리나 알려줘", use_llm=False))
    with_context = understand_query(ROOT, "근거는?", db_path=DB, conversation_state=state, use_llm=False)

    assert selected(with_context)["kind"] == "source_or_evidence_request"
    assert selected(with_context)["route_candidate"] == "source_reader"
    assert selected(with_context)["source_readable"] is True


def test_query_understanding_textmap_only_candidate_is_not_source_readable(monkeypatch) -> None:
    def fake_search(*_args, **_kwargs):
        return [
            {
                "result_type": "textmap",
                "id": "TextMap_TEST",
                "textmap_id": "TextMap_TEST",
                "language": "ko",
                "text": "테스트 텍스트맵 결과",
                "rank": -1.0,
            }
        ]

    monkeypatch.setattr("genshin_lore_db.search_engine.query_understanding.search_project_amber_v2", fake_search)

    result = understand_query(ROOT, "zztextmaponly", db_path=DB, use_llm=False)
    textmap_candidates = [
        item
        for item in result["candidates"]
        if "textmap_only_not_source_readable" in item.get("risk_flags", [])
    ]

    assert textmap_candidates
    assert textmap_candidates[0]["source_readable"] is False
    assert selected(result)["kind"] != "supported_entity"


def test_query_understanding_llm_cannot_invent_basic_lookup(monkeypatch) -> None:
    def fake_ollama_chat(*_args, **_kwargs):
        return {
            "ok": True,
            "content": '{"selected_candidate_id":"invented:avatar","route":"basic_lookup","confidence":0.99,"reason":"invented","uncertainty":[],"needs_more_evidence":false}',
            "error": None,
        }

    monkeypatch.setattr("genshin_lore_db.search_engine.query_understanding.ollama_chat", fake_ollama_chat)

    result = understand_query(ROOT, "파네스 알려줘", db_path=DB, use_llm=True)

    assert selected(result)["kind"] == "lore_concept"
    assert selected(result)["route_candidate"] == "analysis"
    assert result["llm_adjudication"]["used"] is True
    assert result["llm_adjudication"]["valid"] is False
    assert result["fallback_used"] is True


def test_query_understanding_llm_unavailable_falls_back_conservatively(monkeypatch) -> None:
    monkeypatch.setattr(
        "genshin_lore_db.search_engine.query_understanding.ollama_chat",
        lambda *_args, **_kwargs: {"ok": False, "error": {"type": "unavailable"}},
    )

    result = understand_query(ROOT, "파네스", db_path=DB, use_llm=True)

    assert selected(result)["kind"] == "lore_concept"
    assert selected(result)["route_candidate"] == "analysis"
    assert result["llm_adjudication"]["used"] is True
    assert result["fallback_used"] is True
