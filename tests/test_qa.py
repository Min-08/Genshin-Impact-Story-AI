from __future__ import annotations

from genshin_lore_db.search_engine.qa import (
    build_character_facts,
    build_reliquary_facts,
    build_weapon_facts,
    draft_answer_from_facts,
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
