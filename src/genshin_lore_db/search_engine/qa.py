from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from genshin_lore_db.io import read_json
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.pipeline.project_amber_v2 import search_project_amber_v2
from genshin_lore_db.search_engine.aliases import normalize_alias
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, rewrite_answer_with_ollama


SUPPORTED_CONTENT_TYPES = {"avatar", "weapon", "reliquary"}
DEFAULT_LANGUAGE = "ko"

QUERY_HINTS = {
    "기본정보",
    "기본 정보",
    "정보",
    "알려줘",
    "정리",
    "효과",
    "성유물",
    "무기",
    "캐릭터",
}

ELEMENT_LABELS = {
    "Fire": "불",
    "Water": "물",
    "Wind": "바람",
    "Electric": "번개",
    "Grass": "풀",
    "Ice": "얼음",
    "Rock": "바위",
}

WEAPON_TYPE_LABELS = {
    "WEAPON_SWORD_ONE_HAND": "한손검",
    "WEAPON_CLAYMORE": "양손검",
    "WEAPON_POLE": "장병기",
    "WEAPON_BOW": "활",
    "WEAPON_CATALYST": "법구",
}

REGION_LABELS = {
    "MONDSTADT": "몬드",
    "LIYUE": "리월",
    "INAZUMA": "이나즈마",
    "SUMERU": "수메르",
    "FONTAINE": "폰타인",
    "NATLAN": "나타",
    "FATUI": "우인단",
    "MAINACTOR": "여행자",
}

PROP_LABELS = {
    "FIGHT_PROP_BASE_ATTACK": "기초 공격력",
    "FIGHT_PROP_ATTACK_PERCENT": "공격력",
    "FIGHT_PROP_HP_PERCENT": "HP",
    "FIGHT_PROP_DEFENSE_PERCENT": "방어력",
    "FIGHT_PROP_CRITICAL": "치명타 확률",
    "FIGHT_PROP_CRITICAL_HURT": "치명타 피해",
    "FIGHT_PROP_CHARGE_EFFICIENCY": "원소 충전 효율",
    "FIGHT_PROP_ELEMENT_MASTERY": "원소 마스터리",
    "FIGHT_PROP_PHYSICAL_ADD_HURT": "물리 피해 보너스",
    "FIGHT_PROP_HEAL_ADD": "치유 보너스",
}


def answer_question(
    root: Path | str,
    query: str,
    *,
    use_llm: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    db_path: Path | None = None,
    language: str = DEFAULT_LANGUAGE,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    search_db = db_path or root_path / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
    resolution = resolve_qa_target(search_db, query, language=language)
    if not resolution:
        return unsupported_answer(query, search_db)

    raw_path = Path(resolution["raw_ref"])
    raw_record = read_json(raw_path)
    facts = build_facts(raw_record, resolution)
    draft_answer = draft_answer_from_facts(facts)
    llm_state: dict[str, Any] = {
        "enabled": use_llm,
        "used": False,
        "model": model,
        "ok": False,
        "error": None,
    }
    validation = validate_answer(draft_answer, facts, draft_answer)
    final_answer = draft_answer

    if use_llm:
        llm_result = rewrite_answer_with_ollama(facts=facts, draft_answer=draft_answer, model=model)
        llm_state.update(
            {
                "ok": bool(llm_result.get("ok")),
                "error": llm_result.get("error"),
            }
        )
        if llm_result.get("ok"):
            llm_validation = validate_answer(str(llm_result.get("content") or ""), facts, draft_answer)
            llm_state["validation"] = llm_validation
            if llm_validation["ok"]:
                final_answer = str(llm_result["content"]).strip()
                llm_state["used"] = True
                validation = llm_validation
            else:
                llm_state["error"] = {
                    "type": "validation_failed",
                    "message": "; ".join(llm_validation["reasons"]),
                }
                validation = validate_answer(final_answer, facts, draft_answer)

    return {
        "query": query,
        "intent": facts["intent"],
        "facts": facts,
        "draft_answer": draft_answer,
        "final_answer": final_answer,
        "llm": llm_state,
        "validation": validation,
        "sources": facts["sources"],
    }


def resolve_qa_target(db_path: Path, query: str, *, language: str = DEFAULT_LANGUAGE) -> dict[str, Any] | None:
    if not db_path.exists():
        return None
    rows = title_candidates(db_path, language=language)
    query_norm = normalize_alias(strip_query_hints(query))
    original_norm = normalize_alias(query)
    scored = []
    for row in rows:
        title = str(row.get("title") or "")
        title_norm = normalize_alias(title)
        if not title_norm:
            continue
        score = 0
        if title_norm in original_norm:
            score += len(title_norm) * 10
        if title_norm in query_norm:
            score += len(title_norm) * 12
        token_score = sum(1 for token in title.split() if normalize_alias(token) in original_norm)
        score += token_score * 4
        score += content_type_hint_score(query, str(row.get("content_type") or ""))
        if score > 0:
            scored.append((score, len(title_norm), row))
    if scored:
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return dict(scored[0][2])

    for content_type in preferred_content_types(query):
        hits = search_project_amber_v2(
            db_path,
            strip_query_hints(query),
            language=language,
            content_type=content_type,
            limit=1,
        )
        if hits:
            return localization_for_canonical(db_path, str(hits[0]["canonical_id"]), language=language)
    return None


def title_candidates(db_path: Path, *, language: str) -> list[dict[str, Any]]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [
        dict(row)
        for row in conn.execute(
            """
            SELECT l.canonical_id, l.language, l.title, l.source_url, l.raw_ref,
                   i.content_type, i.item_id, i.rank, i.route
            FROM localizations l
            JOIN items i ON i.canonical_id = l.canonical_id
            WHERE l.language = ?
              AND i.content_type IN ('avatar', 'weapon', 'reliquary')
              AND l.raw_ref IS NOT NULL
              AND l.title IS NOT NULL
            """,
            (language,),
        )
    ]
    conn.close()
    return rows


def localization_for_canonical(db_path: Path, canonical_id: str, *, language: str) -> dict[str, Any] | None:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT l.canonical_id, l.language, l.title, l.source_url, l.raw_ref,
               i.content_type, i.item_id, i.rank, i.route
        FROM localizations l
        JOIN items i ON i.canonical_id = l.canonical_id
        WHERE l.canonical_id = ? AND l.language = ?
        """,
        (canonical_id, language),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def strip_query_hints(query: str) -> str:
    stripped = str(query)
    for hint in sorted(QUERY_HINTS, key=len, reverse=True):
        stripped = stripped.replace(hint, " ")
    return clean_text(stripped)


def preferred_content_types(query: str) -> list[str]:
    normalized = normalize_alias(query)
    if "성유물" in normalized:
        return ["reliquary", "weapon", "avatar"]
    if "무기" in normalized:
        return ["weapon", "reliquary", "avatar"]
    if "캐릭터" in normalized:
        return ["avatar", "weapon", "reliquary"]
    if "효과" in normalized:
        return ["reliquary", "weapon", "avatar"]
    return ["avatar", "weapon", "reliquary"]


def content_type_hint_score(query: str, content_type: str) -> int:
    normalized = normalize_alias(query)
    if content_type == "reliquary" and ("성유물" in normalized or "효과" in normalized):
        return 8
    if content_type == "weapon" and ("무기" in normalized or "효과" in normalized):
        return 6
    if content_type == "avatar" and ("캐릭터" in normalized or "기본정보" in normalized):
        return 6
    return 0


def build_facts(raw_record: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    payload = raw_record.get("payload") or {}
    source = source_from_raw(raw_record, resolution)
    content_type = str(resolution.get("content_type") or raw_record.get("metadata", {}).get("content_type") or "")
    if content_type == "reliquary":
        return build_reliquary_facts(payload, source=source)
    if content_type == "weapon":
        return build_weapon_facts(payload, source=source)
    if content_type == "avatar":
        return build_character_facts(payload, source=source)
    raise ValueError(f"Unsupported QA content type: {content_type}")


def build_reliquary_facts(payload: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    affix_list = payload.get("affixList") or {}
    effects = []
    for index, key in enumerate(sorted(affix_list), start=1):
        effects.append(
            {
                "id": str(key),
                "pieces": 2 if index == 1 else 4 if index == 2 else None,
                "text": clean_text(affix_list[key]),
            }
        )
    pieces = []
    suit = payload.get("suit") or {}
    for slot, item in sorted(suit.items()):
        pieces.append(
            {
                "slot": slot,
                "name": clean_text(item.get("name") or ""),
                "description": clean_text(item.get("description") or ""),
            }
        )
    acquisition = [
        clean_text(item.get("name") or "")
        for item in payload.get("source") or []
        if isinstance(item, dict) and item.get("name")
    ]
    return {
        "intent": "reliquary_effect_lookup",
        "content_type": "reliquary",
        "name": clean_text(payload.get("name") or ""),
        "item_id": str(payload.get("id") or ""),
        "rank": payload.get("rank"),
        "effects": effects,
        "pieces": pieces,
        "acquisition": acquisition,
        "sources": [source],
    }


def build_weapon_facts(payload: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    affixes = []
    for affix_id, affix in sorted((payload.get("affix") or {}).items()):
        upgrades = affix.get("upgrade") or {}
        affixes.append(
            {
                "id": str(affix_id),
                "name": clean_text(affix.get("name") or ""),
                "refinements": [
                    {
                        "level": int(level) + 1 if str(level).isdigit() else level,
                        "text": clean_text(text),
                    }
                    for level, text in sorted(upgrades.items(), key=lambda pair: str(pair[0]))
                ],
            }
        )
    return {
        "intent": "weapon_basic_info",
        "content_type": "weapon",
        "name": clean_text(payload.get("name") or ""),
        "item_id": str(payload.get("id") or ""),
        "rank": payload.get("rank"),
        "weapon_type": clean_text(payload.get("type") or ""),
        "description": clean_text(payload.get("description") or ""),
        "special_prop": prop_label(payload.get("specialProp")),
        "base_props": base_props(payload),
        "affixes": affixes,
        "sources": [source],
    }


def build_character_facts(payload: dict[str, Any], *, source: dict[str, Any]) -> dict[str, Any]:
    fetter = payload.get("fetter") or {}
    return {
        "intent": "character_basic_info",
        "content_type": "avatar",
        "name": clean_text(payload.get("name") or ""),
        "item_id": str(payload.get("id") or ""),
        "rank": payload.get("rank"),
        "element": ELEMENT_LABELS.get(str(payload.get("element") or ""), payload.get("element")),
        "weapon_type": WEAPON_TYPE_LABELS.get(str(payload.get("weaponType") or ""), payload.get("weaponType")),
        "region": REGION_LABELS.get(str(payload.get("region") or ""), payload.get("region")),
        "birthday": format_birthday(payload.get("birthday")),
        "title": clean_text(fetter.get("title") or ""),
        "detail": clean_text(fetter.get("detail") or ""),
        "native": clean_text(fetter.get("native") or ""),
        "constellation": clean_text(fetter.get("constellation") or ""),
        "cv": fetter.get("cv") or {},
        "special_prop": prop_label(payload.get("specialProp")),
        "sources": [source],
    }


def source_from_raw(raw_record: dict[str, Any], resolution: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_level": "L0",
        "source": raw_record.get("source") or "project_amber",
        "source_url": raw_record.get("source_url") or resolution.get("source_url"),
        "raw_ref": str(resolution.get("raw_ref") or ""),
        "language": raw_record.get("language") or resolution.get("language"),
    }


def base_props(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in (payload.get("upgrade") or {}).get("prop") or []:
        rows.append(
            {
                "prop": prop_label(row.get("propType")),
                "initial_value": row.get("initValue"),
            }
        )
    return rows


def prop_label(value: Any) -> str | None:
    if value is None:
        return None
    return PROP_LABELS.get(str(value), str(value))


def format_birthday(value: Any) -> str | None:
    if isinstance(value, list) and len(value) == 2:
        return f"{value[0]}월 {value[1]}일"
    return None


def draft_answer_from_facts(facts: dict[str, Any]) -> str:
    intent = facts.get("intent")
    if intent == "reliquary_effect_lookup":
        return draft_reliquary_answer(facts)
    if intent == "weapon_basic_info":
        return draft_weapon_answer(facts)
    if intent == "character_basic_info":
        return draft_character_answer(facts)
    return f"{facts.get('name') or '해당 항목'} 정보를 찾았습니다."


def draft_reliquary_answer(facts: dict[str, Any]) -> str:
    lines = [f"{with_topic_particle(facts['name'])} 성유물 세트입니다."]
    for effect in facts.get("effects") or []:
        label = f"{effect['pieces']}세트" if effect.get("pieces") else effect["id"]
        lines.append(f"- {label}: {effect['text']}")
    piece_names = [piece["name"] for piece in facts.get("pieces") or [] if piece.get("name")]
    if piece_names:
        lines.append(f"- 구성 부위: {', '.join(piece_names)}")
    if facts.get("acquisition"):
        lines.append(f"- 획득처: {', '.join(facts['acquisition'])}")
    lines.append(source_line(facts))
    return "\n".join(lines)


def draft_weapon_answer(facts: dict[str, Any]) -> str:
    lines = [f"{with_topic_particle(facts['name'])} {facts.get('rank')}성 {facts.get('weapon_type')}입니다."]
    if facts.get("description"):
        lines.append(f"- 설명: {facts['description']}")
    if facts.get("special_prop"):
        lines.append(f"- 보조 속성: {facts['special_prop']}")
    affixes = facts.get("affixes") or []
    if affixes:
        affix = affixes[0]
        lines.append(f"- 무기 효과: {affix.get('name') or affix.get('id')}")
        refinements = affix.get("refinements") or []
        if refinements:
            lines.append(f"- 1재련 효과: {refinements[0]['text']}")
    lines.append(source_line(facts))
    return "\n".join(lines)


def draft_character_answer(facts: dict[str, Any]) -> str:
    lines = [f"{with_topic_particle(facts['name'])} {facts.get('rank')}성 캐릭터입니다."]
    basics = []
    for key, label in [
        ("element", "원소"),
        ("weapon_type", "무기"),
        ("region", "지역"),
        ("birthday", "생일"),
        ("constellation", "운명의 자리"),
        ("special_prop", "돌파 보너스"),
    ]:
        if facts.get(key):
            basics.append(f"{label}: {facts[key]}")
    if basics:
        lines.append("- " + " / ".join(basics))
    if facts.get("title"):
        lines.append(f"- 칭호: {facts['title']}")
    if facts.get("detail"):
        lines.append(f"- 소개: {facts['detail']}")
    if facts.get("cv"):
        cvs = facts["cv"]
        parts = [f"{lang}: {name}" for lang, name in sorted(cvs.items()) if name]
        if parts:
            lines.append(f"- CV: {', '.join(parts)}")
    lines.append(source_line(facts))
    return "\n".join(lines)


def source_line(facts: dict[str, Any]) -> str:
    source = (facts.get("sources") or [{}])[0]
    return f"- 출처: {source.get('source') or 'project_amber'} 공식 데이터 ({source.get('language') or 'ko'})"


def with_topic_particle(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    last = text[-1]
    code = ord(last)
    if 0xAC00 <= code <= 0xD7A3:
        has_final = (code - 0xAC00) % 28 != 0
        return text + ("은" if has_final else "는")
    return text + "는"


def validate_answer(answer: str, facts: dict[str, Any], draft_answer: str) -> dict[str, Any]:
    reasons = []
    cleaned = clean_text(answer)
    if not cleaned:
        reasons.append("empty_answer")
    primary_name = str(facts.get("name") or "").strip()
    if primary_name and primary_name not in cleaned:
        reasons.append(f"missing_primary_name:{primary_name}")
    draft_cleaned = clean_text(draft_answer)
    if draft_cleaned and len(cleaned) > int(len(draft_cleaned) * 1.35):
        reasons.append("answer_too_long")
    if primary_name and cleaned.count(primary_name) > draft_cleaned.count(primary_name) + 1:
        reasons.append(f"repeated_primary_name:{primary_name}")

    allowed_numbers = extract_numbers(json.dumps(facts, ensure_ascii=False) + "\n" + draft_answer)
    answer_numbers = extract_numbers(cleaned)
    unexpected_numbers = sorted(answer_numbers - allowed_numbers - set(str(index) for index in range(1, 11)))
    if unexpected_numbers:
        reasons.append("unexpected_numbers:" + ",".join(unexpected_numbers))

    allowed_text = json.dumps(facts, ensure_ascii=False) + "\n" + draft_answer
    unexpected_quoted = [
        value
        for value in extract_quoted_names(cleaned)
        if value and value not in allowed_text
    ]
    if unexpected_quoted:
        reasons.append("unexpected_quoted_names:" + ",".join(sorted(set(unexpected_quoted))))

    forbidden_terms = ["아마", "추측입니다", "추측으로", "가능성이", "추천", "권장 세팅", "티어"]
    used_forbidden = [term for term in forbidden_terms if term in cleaned]
    if used_forbidden:
        reasons.append("forbidden_terms:" + ",".join(used_forbidden))

    return {
        "ok": not reasons,
        "reasons": reasons,
    }


def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", text))


def extract_quoted_names(text: str) -> list[str]:
    rows = []
    rows.extend(re.findall(r"「([^」]{1,40})」", text))
    rows.extend(re.findall(r'"([^"]{1,40})"', text))
    return [clean_text(row) for row in rows]


def unsupported_answer(query: str, db_path: Path) -> dict[str, Any]:
    message = "지원하는 정답형 QA 대상을 찾지 못했습니다. 현재는 성유물, 무기, 캐릭터 기본정보를 지원합니다."
    return {
        "query": query,
        "intent": "unsupported",
        "facts": {},
        "draft_answer": message,
        "final_answer": message,
        "llm": {
            "enabled": False,
            "used": False,
            "model": DEFAULT_OLLAMA_MODEL,
            "ok": False,
            "error": {"type": "unsupported_query", "message": message},
        },
        "validation": {"ok": True, "reasons": []},
        "sources": [{"db_path": str(db_path)}],
    }
