from __future__ import annotations

from genshin_lore_db.search_engine.conversation import ConversationState
from genshin_lore_db.search_engine.qa import (
    answer_question,
    build_character_facts,
    build_reliquary_facts,
    build_weapon_facts,
    draft_answer_from_facts,
    route_answer_query,
    validate_answer,
)


SOURCE = {
    "source_level": "L0",
    "source": "project_amber",
    "source_url": "https://example.test",
    "raw_ref": "raw.json",
    "language": "ko",
}


def test_reliquary_facts_extract_affixes() -> None:
    facts = build_reliquary_facts(
        {
            "id": 15020,
            "name": "절연의 기치",
            "affixList": {
                "2150200": "원소 충전 효율+20%",
                "2150201": "원소폭발 피해가 최대 75%까지 증가한다",
            },
            "suit": {"EQUIP_RING": {"name": "진홍의 주전자", "description": "정교한 술주전자"}},
            "source": [{"name": "성유물 반환의 신비 획득"}],
        },
        source=SOURCE,
    )
    assert facts["intent"] == "reliquary_effect_lookup"
    assert facts["effects"][0]["pieces"] == 2
    assert facts["effects"][0]["text"] == "원소 충전 효율+20%"
    assert facts["effects"][1]["pieces"] == 4
    assert facts["pieces"][0]["name"] == "진홍의 주전자"


def test_weapon_facts_extract_refinement_effect() -> None:
    facts = build_weapon_facts(
        {
            "id": 11509,
            "name": "안개를 가르는 회광",
            "rank": 5,
            "type": "한손검",
            "description": "차가운 자색으로 반짝이는 태도",
            "specialProp": "FIGHT_PROP_CRITICAL_HURT",
            "affix": {"111509": {"name": "무절 어검", "upgrade": {"0": "모든 원소 피해 보너스 12%"}}},
        },
        source=SOURCE,
    )
    assert facts["intent"] == "weapon_basic_info"
    assert facts["special_prop"] == "치명타 피해"
    assert facts["affixes"][0]["refinements"][0]["level"] == 1
    assert facts["affixes"][0]["refinements"][0]["text"] == "모든 원소 피해 보너스 12%"


def test_weapon_answer_default_uses_r1_only_and_detail_includes_all_refinements() -> None:
    facts = build_weapon_facts(
        {
            "id": 11509,
            "name": "안개를 가르는 회광",
            "rank": 5,
            "type": "한손검",
            "specialProp": "FIGHT_PROP_CRITICAL_HURT",
            "affix": {
                "111509": {
                    "name": "무절 어검",
                    "upgrade": {
                        "0": "피해 보너스 12%",
                        "1": "피해 보너스 15%",
                        "2": "피해 보너스 18%",
                        "3": "피해 보너스 21%",
                        "4": "피해 보너스 24%",
                    },
                }
            },
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    detail = draft_answer_from_facts(facts, requested_style="detail")

    assert "R1: 피해 보너스 12%" in draft
    assert "R5: 피해 보너스 24%" not in draft
    assert "R1: 피해 보너스 12%" in detail
    assert "R5: 피해 보너스 24%" in detail


def test_draft_answers_avoid_korean_sentence_and_particle_regressions() -> None:
    reliquary_facts = build_reliquary_facts(
        {
            "id": 15020,
            "name": "절연의 기치",
            "affixList": {"2150201": "최대 75%까지 증가할 수 있다"},
        },
        source=SOURCE,
    )
    reliquary_answer = draft_answer_from_facts(reliquary_facts)
    assert "증가할 수 있다입니다" not in reliquary_answer
    assert "증가할 수 있다." in reliquary_answer

    weapon_facts = build_weapon_facts(
        {
            "id": 14501,
            "name": "테스트 법구",
            "rank": 5,
            "type": "법구",
            "description": "이름이 이렇게 붙은 것은 과거 때문이다",
        },
        source=SOURCE,
    )
    weapon_answer = draft_answer_from_facts(weapon_facts)
    assert "과거 때문이다입니다" not in weapon_answer
    assert "과거 때문이다." in weapon_answer

    character_facts = build_character_facts(
        {
            "id": 10000089,
            "name": "푸리나",
            "rank": 5,
            "element": "Water",
            "weaponType": "WEAPON_CATALYST",
            "fetter": {"detail": "심판 무대 위의 주인공"},
        },
        source=SOURCE,
    )
    character_answer = draft_answer_from_facts(character_facts)
    assert "법구을" not in character_answer
    assert "법구를 사용합니다" in character_answer
    assert "주인공라고" not in character_answer
    assert "주인공이라고" in character_answer

    sentence_detail_facts = build_character_facts(
        {
            "id": 10000073,
            "name": "나히다",
            "rank": 5,
            "weaponType": "WEAPON_CATALYST",
            "fetter": {"detail": "꿈속에서만 세상을 자유롭게 바라볼 수 있다"},
        },
        source=SOURCE,
    )
    sentence_detail_answer = draft_answer_from_facts(sentence_detail_facts)
    assert "있다라고" not in sentence_detail_answer
    assert "있다고 적혀 있습니다" in sentence_detail_answer


def test_character_facts_extract_basic_profile() -> None:
    facts = build_character_facts(
        {
            "id": 10000089,
            "name": "푸리나",
            "rank": 5,
            "element": "Water",
            "weaponType": "WEAPON_SWORD_ONE_HAND",
            "region": "FONTAINE",
            "birthday": [10, 13],
            "specialProp": "FIGHT_PROP_CRITICAL",
            "fetter": {
                "title": "멈추지 않는 독무",
                "detail": "심판 무대 위의 주인공",
                "constellation": "코레고스자리",
                "cv": {"KR": "김하영"},
            },
        },
        source=SOURCE,
    )
    assert facts["intent"] == "character_basic_info"
    assert facts["element"] == "물"
    assert facts["weapon_type"] == "한손검"
    assert facts["birthday"] == "10월 13일"


def test_character_facts_extract_constellations_and_talents() -> None:
    facts = build_character_facts(
        {
            "id": 10000089,
            "name": "푸리나",
            "rank": 5,
            "element": "Water",
            "weaponType": "WEAPON_SWORD_ONE_HAND",
            "fetter": {"constellation": "코레고스자리"},
            "constellation": {
                "0": {"name": "사랑은 새", "description": "무대 열기를 획득한다"},
                "1": {"name": "부평초", "description": "HP 최대치가 증가한다"},
            },
            "talent": {
                "0": {"name": "독무자의 초대", "description": "일반 공격을 한다"},
                "1": {"name": "고고한 살롱", "description": "손님을 초대한다"},
            },
        },
        source=SOURCE,
        intent="character_constellation",
    )

    assert facts["constellations"][0]["level"] == 1
    assert facts["constellations"][0]["name"] == "사랑은 새"
    assert facts["talents"][1]["name"] == "고고한 살롱"
    assert "C1 사랑은 새" in draft_answer_from_facts(facts)


def test_validator_rejects_new_numbers_and_quoted_names() -> None:
    facts = build_reliquary_facts(
        {
            "id": 15020,
            "name": "절연의 기치",
            "affixList": {"2150200": "원소 충전 효율+20%"},
            "suit": {},
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    invalid = validate_answer("절연의 기치는 「나히다」에게 999% 보너스를 줍니다.", facts, draft)
    assert not invalid["ok"]
    assert any(reason.startswith("unexpected_numbers") for reason in invalid["reasons"])
    assert any(reason.startswith("unexpected_quoted_names") for reason in invalid["reasons"])


def test_validator_rejects_overlong_repeated_rewrite() -> None:
    facts = build_reliquary_facts(
        {
            "id": 15020,
            "name": "절연의 기치",
            "affixList": {"2150200": "원소 충전 효율+20%"},
            "suit": {},
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    invalid = validate_answer(draft + "\n\n" + draft, facts, draft)
    assert not invalid["ok"]
    assert "answer_too_long" in invalid["reasons"]


def test_validator_rejects_missing_required_fact_fragment() -> None:
    facts = build_reliquary_facts(
        {
            "id": 15020,
            "name": "절연의 기치",
            "affixList": {"2150200": "원소 충전 효율+20%"},
            "suit": {},
            "source": [{"name": "성유물 반환의 신비 획득"}],
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    invalid = validate_answer(draft.replace("성유물 반환의 신비 획득", "성유이나물 반환의 신비 획득"), facts, draft)

    assert not invalid["ok"]
    assert any(reason.startswith("missing_fact_fragments:") for reason in invalid["reasons"])


def test_validator_requires_weapon_rank_type_phrase() -> None:
    facts = build_weapon_facts(
        {
            "id": 12502,
            "name": "늑대의 말로",
            "rank": 5,
            "type": "양손검",
            "description": "늑대 기사가 사용하던 대검",
            "specialProp": "FIGHT_PROP_ATTACK_PERCENT",
            "affix": {"112502": {"name": "늑대 같은 사냥꾼", "upgrade": {"0": "공격력+20%"}}},
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    invalid = validate_answer(
        draft.replace("늑대의 말로는 5성 양손검입니다.", "- 이름: 늑대의 말로\n- 랭크: 5\n- 무기 종류: 양손검"),
        facts,
        draft,
    )

    assert not invalid["ok"]
    assert any("5성 양손검" in reason for reason in invalid["reasons"])


def test_validator_requires_character_region_value() -> None:
    facts = build_character_facts(
        {
            "id": 10000052,
            "name": "라이덴 쇼군",
            "rank": 5,
            "element": "Electric",
            "weaponType": "WEAPON_POLE",
            "region": "INAZUMA",
            "birthday": [6, 26],
            "specialProp": "FIGHT_PROP_CHARGE_EFFICIENCY",
            "fetter": {
                "title": "일심정토",
                "detail": "이나즈마 백성들에게 변치 않는 「영원」을 약속했다",
                "constellation": "천하인자리",
            },
        },
        source=SOURCE,
    )
    draft = draft_answer_from_facts(facts)
    invalid = validate_answer(draft.replace("이나즈마", "이나즈가"), facts, draft)

    assert not invalid["ok"]
    assert any("이나즈마" in reason for reason in invalid["reasons"])


def test_route_answer_query_guards_greeting() -> None:
    route = route_answer_query(".", "안녕", use_llm=False)

    assert route["mode"] == "chitchat"
    assert route["intent"] == "small_talk"
    assert "guard:greeting" in route["signals"]


def test_route_answer_query_hard_guard_blocks_llm_basic_lookup(monkeypatch) -> None:
    def fake_semantic_parse(*_args, **_kwargs):
        return {
            "ok": True,
            "parse": {
                "route": "basic_lookup",
                "intent": "character_basic_info",
                "entities": [{"surface": "나선비경", "content_type_hint": "avatar", "confidence": 0.9}],
                "requested_style": "default",
                "confidence": 0.9,
            },
        }

    monkeypatch.setattr(
        "genshin_lore_db.search_engine.qa.parse_query_semantics_with_ollama",
        fake_semantic_parse,
    )

    route = route_answer_query(".", "나선비경 티어 알려줘", use_llm=True)

    assert route["mode"] == "unsupported"
    assert route["intent"] == "guide_or_meta_request"
    assert route["unsupported_reason"] == "unofficial_strategy_request"


def test_route_answer_query_blocks_artifact_recommendation_lookup() -> None:
    route = route_answer_query(".", "피슬 성유물 추천해줘", use_llm=False)

    assert route["mode"] == "unsupported"
    assert route["intent"] == "guide_or_meta_request"
    assert route["unsupported_reason"] == "unofficial_strategy_request"


def test_route_answer_query_basic_summary_phrase_is_brief_lookup() -> None:
    route = route_answer_query(".", "푸리나에 대해서 요약해줘", use_llm=False)

    assert route["mode"] == "basic_lookup"
    assert route["intent"] == "character_basic_info"
    assert route["requested_style"] == "brief"


def test_route_answer_query_exact_character_defaults_to_basic_lookup() -> None:
    route = route_answer_query(".", "아야카에 대해서 알려줘", use_llm=False)

    assert route["mode"] == "basic_lookup"
    assert route["intent"] == "character_basic_info"


def test_lore_terms_do_not_promote_to_basic_lookup_entities() -> None:
    cases = [
        ("운명의 베틀 알려줘", "여행자"),
        ("니벨룽겐 알려줘", "느비예트"),
    ]

    for query, forbidden_name in cases:
        result = answer_question(".", query, use_llm=False)

        assert result["intent"] == "unsupported"
        assert result["canonical_id"] is None
        assert result["content_type"] is None
        assert result["route"]["mode"] != "basic_lookup"
        assert result["route"]["answer_plan"]["route"] != "basic_lookup"
        assert forbidden_name not in result["final_answer"]


def test_llm_basic_lookup_without_db_resolution_is_not_authoritative(monkeypatch) -> None:
    def fake_semantic_parse(*_args, **_kwargs):
        return {
            "ok": True,
            "parse": {
                "route": "basic_lookup",
                "intent": "character_basic_info",
                "entities": [{"surface": "파네스", "content_type_hint": "avatar", "confidence": 0.9}],
                "requested_style": "default",
                "confidence": 0.9,
            },
        }

    monkeypatch.setattr(
        "genshin_lore_db.search_engine.qa.parse_query_semantics_with_ollama",
        fake_semantic_parse,
    )

    route = route_answer_query(".", "파네스 알려줘", use_llm=True)
    assert route["mode"] == "analysis"
    assert route["answer_plan"]["route"] == "analysis"
    assert route["unsupported_reason"] == "route_not_implemented"

    result = answer_question(".", "파네스 알려줘", use_llm=True)
    assert result["intent"] == "unsupported"
    assert result["canonical_id"] is None
    assert result["content_type"] is None
    assert result["route"]["mode"] == "analysis"
    assert result["answer_plan"]["route"] == "analysis"


def test_generic_category_query_requires_specific_entity() -> None:
    result = answer_question(".", "성유물에 대해서 알려줘", use_llm=False)

    assert result["canonical_id"] is None
    assert result["content_type"] is None
    assert result["route"]["mode"] == "unsupported"
    assert result["route"]["needs_clarification"] is True
    assert result["route"]["unsupported_reason"] == "clarification_required_entity"
    assert "구체적인 이름" in result["final_answer"]


def test_avatar_effect_query_does_not_fallback_to_reliquary() -> None:
    result = answer_question(".", "아야카의 돌파효과에 대해서 알려줘", use_llm=False)

    assert result["canonical_id"] is None
    assert result["content_type"] is None
    assert result["route"]["mode"] == "unsupported"
    assert result["route"]["needs_clarification"] is True
    assert result["route"]["unsupported_reason"] == "ambiguous_avatar_ascension"
    assert "돌파 보너스" in result["final_answer"]


def test_exact_character_constellation_still_basic_lookup() -> None:
    result = answer_question(".", "아야카 별자리", use_llm=False)

    assert result["route"]["mode"] == "basic_lookup"
    assert result["intent"] == "character_constellation"
    assert result["content_type"] == "avatar"
    assert result["canonical_id"] == "project_amber:avatar:10000002"


def test_intent_only_query_without_context_requires_clarification() -> None:
    result = answer_question(".", "별자리", use_llm=False)

    assert result["canonical_id"] is None
    assert result["route"]["mode"] == "unsupported"
    assert result["route"]["needs_clarification"] is True
    assert result["route"]["unsupported_reason"] == "clarification_required_entity"


def test_intent_only_followup_uses_active_entity() -> None:
    state = ConversationState()
    first = answer_question(".", "아야카에 대해서 알려줘", use_llm=False, conversation_state=state)
    state.update_from_result(first)

    result = answer_question(".", "별자리", use_llm=False, conversation_state=state)

    assert result["route"]["mode"] == "basic_lookup"
    assert result["route"]["context_used"] is True
    assert result["resolved_query"] == "카미사토 아야카 별자리"
    assert result["intent"] == "character_constellation"
    assert result["content_type"] == "avatar"
    assert result["canonical_id"] == "project_amber:avatar:10000002"


def test_conversation_state_resolves_story_detail_and_evidence_followups() -> None:
    state = ConversationState()
    first = answer_question(".", "푸리나 알려줘", use_llm=False, conversation_state=state)
    state.update_from_result(first)

    story = answer_question(".", "스토리도 알려줘", use_llm=False, conversation_state=state)
    assert story["route"]["mode"] == "summary"
    assert story["route"]["context_used"] is True
    assert story["route"]["answer_plan"]["intent"] == "character_story_summary"
    assert story["route"]["unsupported_reason"] == "route_not_implemented"
    state.update_from_result(story)

    detail = answer_question(".", "더 자세히", use_llm=False, conversation_state=state)
    assert detail["route"]["mode"] == "basic_lookup"
    assert detail["route"]["context_used"] is True
    assert detail["requested_style"] == "detail"
    state.update_from_result(detail)

    evidence = answer_question(".", "근거는?", use_llm=False, conversation_state=state)
    assert evidence["route"]["mode"] == "source_reader"
    assert evidence["route"]["context_used"] is True
    assert evidence["intent"] == "show_evidence"
    assert "project_amber" in evidence["final_answer"]


def test_answer_question_handles_greeting_without_lookup() -> None:
    result = answer_question(".", "안녕", use_llm=False)

    assert result["intent"] == "small_talk"
    assert result["canonical_id"] is None
    assert "말라니" not in result["final_answer"]
