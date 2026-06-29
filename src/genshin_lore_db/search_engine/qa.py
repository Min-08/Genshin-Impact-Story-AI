from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from genshin_lore_db.io import read_json
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.search_engine.answer_plan import AnswerPlan, normalize_answer_plan
from genshin_lore_db.search_engine.aliases import normalize_alias
from genshin_lore_db.search_engine.conversation import ConversationState
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, rewrite_answer_with_ollama
from genshin_lore_db.search_engine.router import is_greeting_query, route_query
from genshin_lore_db.search_engine.semantic import parse_query_semantics_with_ollama


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
    "대해서",
    "누구야",
    "뭐야",
}

STRUCTURED_FORMAT_TERMS = {
    "정리",
    "목록",
    "리스트",
    "표",
    "핵심만",
}

TABLE_FORMAT_TERMS = {"표"}
CONSTELLATION_TERMS = {"별자리", "운명의 자리", "운명의자리", "돌파 효과", "돌파효과"}
TALENT_TERMS = {"특성", "스킬", "전투 특성", "패시브"}

UNSUPPORTED_ANSWER_TERMS = {
    "추천",
    "티어",
    "세팅",
    "파티",
    "조합",
    "메타",
    "딜사이클",
    "나선비경",
    "공략",
    "육성법",
    "성능",
}

STORY_SUMMARY_TERMS = {"스토리", "줄거리", "마신임무", "임무", "퀘스트", "전설임무", "내용"}
BRIEF_STYLE_TERMS = {"요약", "간단", "간단히", "짧게", "핵심만"}
DETAIL_STYLE_TERMS = {"자세히", "전체", "전부", "R1", "R2", "R3", "R4", "R5", "r1", "r2", "r3", "r4", "r5", "제련", "제련별", "수치"}
RAW_STYLE_TERMS = {"원문", "raw", "RAW", "그대로"}
EVIDENCE_STYLE_TERMS = {"근거", "출처", "source", "evidence"}
SOURCE_READER_TERMS = set(EVIDENCE_STYLE_TERMS) | set(RAW_STYLE_TERMS)
GENERIC_LOOKUP_CATEGORY_TERMS = {"성유물", "무기", "캐릭터"}
LOW_INFORMATION_REMAINDERS = {"", "에", "에대해", "에대해서", "의", "은", "는", "을", "를", "가", "이"}
ASCENSION_EFFECT_TERMS = {"돌파효과", "돌파 효과"}
ASCENSION_BONUS_TERMS = {"돌파보너스", "돌파 보너스"}
INTENT_ONLY_FOLLOWUP_TERMS = set(CONSTELLATION_TERMS) | set(TALENT_TERMS) | {"제련", "C1", "C2", "C3", "C4", "C5", "C6", "c1", "c2", "c3", "c4", "c5", "c6"}
FOLLOWUP_FILLER_TERMS = {"더", "좀", "부터", "까지", "보여줘", "알려줘", "해줘", "효과"}
FOLLOWUP_SUFFIXES = ("으로", "로", "도", "은", "는", "이", "가", "을", "를", "좀")

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
    "FIGHT_PROP_FIRE_ADD_HURT": "불 원소 피해 보너스",
    "FIGHT_PROP_WATER_ADD_HURT": "물 원소 피해 보너스",
    "FIGHT_PROP_GRASS_ADD_HURT": "풀 원소 피해 보너스",
    "FIGHT_PROP_ELEC_ADD_HURT": "번개 원소 피해 보너스",
    "FIGHT_PROP_WIND_ADD_HURT": "바람 원소 피해 보너스",
    "FIGHT_PROP_ICE_ADD_HURT": "얼음 원소 피해 보너스",
    "FIGHT_PROP_ROCK_ADD_HURT": "바위 원소 피해 보너스",
}


def answer_question(
    root: Path | str,
    query: str,
    *,
    use_llm: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    db_path: Path | None = None,
    language: str = DEFAULT_LANGUAGE,
    conversation_state: ConversationState | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    search_db = db_path or root_path / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
    route = route_answer_query(
        root_path,
        query,
        use_llm=use_llm,
        model=model,
        db_path=search_db,
        language=language,
        conversation_state=conversation_state,
    )
    if route.get("mode") == "chitchat":
        return small_talk_answer(query, search_db, route=route)
    if route.get("mode") == "source_reader":
        return evidence_answer(query, search_db, route=route, conversation_state=conversation_state)
    if route.get("mode") != "basic_lookup":
        return unsupported_answer(query, search_db, route=route)
    if not should_attempt_basic_lookup(query, route=route):
        return unsupported_answer(query, search_db, route=route)
    lookup_query = str(route.get("resolved_query") or query)
    resolution = None if contains_unsupported_answer_term(query) else resolve_qa_target(search_db, lookup_query, language=language)
    if not resolution:
        return unsupported_answer(query, search_db, route=unresolved_basic_lookup_route(route))

    raw_path = Path(resolution["raw_ref"])
    raw_record = read_json(raw_path)
    requested_format = str(route.get("requested_format") or requested_format_for_query(query))
    requested_style = str(route.get("requested_style") or requested_style_for_query(query))
    facts = build_facts(raw_record, resolution, query=lookup_query)
    draft_answer = draft_answer_from_facts(facts, requested_format=requested_format, requested_style=requested_style)
    llm_state: dict[str, Any] = {
        "enabled": use_llm,
        "used": False,
        "model": model,
        "ok": False,
        "error": None,
    }
    validation = validate_answer(draft_answer, facts, draft_answer, requested_style=requested_style)
    final_answer = draft_answer

    if use_llm:
        llm_state["validation"] = validation
        llm_result = rewrite_answer_with_ollama(facts=facts, draft_answer=draft_answer, model=model)
        llm_state.update(
            {
                "ok": bool(llm_result.get("ok")),
                "error": llm_result.get("error"),
            }
        )
        if llm_result.get("ok"):
            candidate_answer = str(llm_result.get("content") or "").strip()
            llm_validation = validate_answer(candidate_answer, facts, draft_answer, requested_style=requested_style)
            llm_state["validation"] = llm_validation
            if llm_validation["ok"]:
                final_answer = candidate_answer
                llm_state["used"] = True
                validation = llm_validation
            else:
                llm_state["candidate_answer"] = candidate_answer
                llm_state["error"] = {
                    "type": "validation_failed",
                    "message": "; ".join(llm_validation["reasons"]),
                }
                validation = validate_answer(final_answer, facts, draft_answer, requested_style=requested_style)

    return {
        "query": query,
        "resolved_query": lookup_query,
        "canonical_id": resolution.get("canonical_id"),
        "content_type": facts.get("content_type") or resolution.get("content_type"),
        "item_id": facts.get("item_id") or resolution.get("item_id"),
        "intent": facts["intent"],
        "facts": facts,
        "draft_answer": draft_answer,
        "final_answer": final_answer,
        "llm": llm_state,
        "validation": validation,
        "sources": facts["sources"],
        "route": route,
        "requested_format": requested_format,
        "requested_style": requested_style,
        "answer_plan": route.get("answer_plan"),
        "semantic_parse": route.get("semantic_parse"),
    }


def route_answer_query(
    root: Path | str,
    query: str,
    *,
    use_llm: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    db_path: Path | None = None,
    language: str = DEFAULT_LANGUAGE,
    conversation_state: ConversationState | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    search_db = db_path or root_path / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
    context = resolve_conversation_context(query, conversation_state)
    effective_query = str(context.get("resolved_query") or query)
    rule = route_query(effective_query).to_dict()
    requested_format = requested_format_for_query(query)
    requested_style = requested_style_for_query(query)
    if context.get("requested_style"):
        requested_style = str(context["requested_style"])

    if rule.get("mode") == "chitchat":
        route = {
            "mode": "chitchat",
            "confidence": 0.98,
            "signals": ["guard:greeting"],
            "reason": "일반 인사말이므로 검색이나 정답형 QA로 보내지 않습니다.",
        }
        plan = AnswerPlan(route="chitchat", intent="small_talk", requested_style=requested_style, confidence=0.98, parser="deterministic")
        return finalize_route(
            route,
            intent="small_talk",
            requested_format=requested_format,
            requested_style=requested_style,
            plan=plan,
            semantic_state=semantic_parse_state("", use_llm=False, model=model),
            context=context,
        )

    if contains_unsupported_answer_term(effective_query):
        route = {
            "mode": "unsupported",
            "confidence": 0.96,
            "signals": ["guard:unsupported_strategy"],
            "reason": "추천, 티어, 세팅, 파티, 조합, 메타, 딜사이클, 나선비경, 공략, 육성법, 성능 요청은 현재 공식 DB 정답형 조회 범위가 아닙니다.",
        }
        plan = AnswerPlan(
            route="unsupported",
            intent="guide_or_meta_request",
            requested_style=requested_style,
            unsupported_reason="unofficial_strategy_request",
            confidence=0.96,
            parser="deterministic",
            context_reference=context.get("context_reference"),
            context_used=bool(context.get("context_used")),
        )
        return finalize_route(
            route,
            intent="guide_or_meta_request",
            requested_format=requested_format,
            requested_style=requested_style,
            plan=plan,
            semantic_state=semantic_parse_state("", use_llm=False, model=model),
            context=context,
        )

    if is_context_only_source_followup(query) and context.get("route") != "source_reader":
        return clarification_route(
            reason="clarification_required_context",
            query=effective_query,
            requested_format=requested_format,
            requested_style=requested_style,
            context=context,
            model=model,
        )

    if context.get("route") == "source_reader":
        source_style = str(context.get("requested_style") or "evidence")
        route = {
            "mode": "source_reader",
            "confidence": 0.88,
            "signals": ["context:last_answer", f"style:{source_style}"],
            "reason": "직전 답변의 출처나 근거를 요청한 후속 질문으로 분류했습니다.",
        }
        plan = AnswerPlan(
            route="source_reader",
            intent="show_evidence",
            requested_style=source_style,
            detail_level="medium",
            context_reference="last_answer",
            context_used=True,
            needs_evidence=True,
            needs_raw_source=source_style == "raw",
            confidence=0.88,
            parser="deterministic",
        )
        return finalize_route(
            route,
            intent="show_evidence",
            requested_format=requested_format,
            requested_style=source_style,
            plan=plan,
            semantic_state=semantic_parse_state("", use_llm=False, model=model),
            context=context,
        )

    clarification_reason = lookup_clarification_reason(effective_query)
    if clarification_reason:
        return clarification_route(
            reason=clarification_reason,
            query=effective_query,
            requested_format=requested_format,
            requested_style=requested_style,
            context=context,
            model=model,
        )

    has_story_summary = looks_like_story_summary(effective_query)
    has_relation_or_research = rule.get("mode") in {"research"} or any(
        str(signal).startswith("relation:") for signal in rule.get("signals") or []
    )
    allow_exact_lookup = not has_relation_or_research and not has_story_summary
    resolution = resolve_qa_target(search_db, effective_query, language=language) if allow_exact_lookup else None
    intent = classify_lookup_intent(effective_query, resolution)
    if resolution and resolution.get("content_type") == "avatar" and is_ambiguous_avatar_ascension_query(effective_query):
        return clarification_route(
            reason="ambiguous_avatar_ascension",
            query=effective_query,
            requested_format=requested_format,
            requested_style=requested_style,
            context=context,
            model=model,
            resolution=resolution,
        )
    if resolution and not has_relation_or_research:
        route = {
            "mode": "basic_lookup",
            "confidence": max(float(rule.get("confidence") or 0.0), 0.88),
            "signals": [*list(rule.get("signals") or []), f"exact_lookup:{resolution.get('content_type')}", f"intent:{intent}"],
            "reason": "지원되는 공식 데이터 엔티티가 정확히 확인되어 정답형 조회로 분류했습니다.",
        }
        plan = AnswerPlan(
            route="basic_lookup",
            intent=intent,
            requested_style=requested_style,
            detail_level=detail_level_for_style(requested_style),
            context_reference=context.get("context_reference"),
            context_used=bool(context.get("context_used")),
            confidence=float(route["confidence"]),
            parser="deterministic",
        )
        return finalize_route(
            route,
            intent=intent,
            requested_format=requested_format,
            requested_style=requested_style,
            plan=plan,
            semantic_state=semantic_parse_state("", use_llm=False, model=model),
            context=context,
            resolution=resolution,
            resolved_query=effective_query,
        )

    if has_story_summary:
        story_resolution = resolve_qa_target(search_db, effective_query, language=language)
        route = {
            "mode": "summary",
            "confidence": max(float(rule.get("confidence") or 0.0), 0.78),
            "signals": [*list(rule.get("signals") or []), "summary_scope:story"],
            "reason": "스토리나 임무 범위 요약 요청으로 분류했습니다.",
        }
        plan = AnswerPlan(
            route="summary",
            intent=summary_intent_for_query(effective_query, story_resolution),
            entities=entities_from_resolution(story_resolution),
            requested_style=requested_style,
            detail_level=detail_level_for_style(requested_style),
            context_reference=context.get("context_reference"),
            context_used=bool(context.get("context_used")),
            unsupported_reason="route_not_implemented",
            confidence=float(route["confidence"]),
            parser="deterministic",
        )
        return finalize_route(
            route,
            intent=plan.intent,
            requested_format=requested_format,
            requested_style=requested_style,
            plan=plan,
            semantic_state=semantic_parse_state("", use_llm=False, model=model),
            context=context,
            resolution=story_resolution,
            resolved_query=effective_query,
            unsupported_reason="route_not_implemented",
        )

    semantic_state = semantic_parse_state(effective_query, use_llm=use_llm, model=model)
    if semantic_is_greeting(semantic_state):
        route = {
            "mode": "chitchat",
            "confidence": 0.98,
            "signals": ["guard:greeting"],
            "reason": "일반 인사말이므로 검색이나 정답형 QA로 보내지 않습니다.",
        }
        plan = AnswerPlan(route="chitchat", intent="small_talk", requested_style=requested_style, confidence=0.98, parser="llm")
        return finalize_route(
            route,
            intent="small_talk",
            requested_format=requested_format,
            requested_style=requested_style,
            plan=plan,
            semantic_state=semantic_state,
            context=context,
        )

    semantic_plan = normalize_answer_plan((semantic_state.get("parse") if isinstance(semantic_state, dict) else None), parser="llm")
    if not has_relation_or_research and semantic_plan and semantic_plan.route in {"basic_lookup", "summary", "analysis", "research"}:
        if semantic_plan.route == "basic_lookup":
            semantic_resolution = resolve_qa_target(search_db, effective_query, language=language)
            if semantic_resolution:
                semantic_intent = classify_lookup_intent(effective_query, semantic_resolution)
                route = semantic_route_candidate(semantic_state) or dict(rule)
                return finalize_route(
                    route,
                    intent=semantic_plan.intent or semantic_intent,
                    requested_format=requested_format,
                    requested_style=semantic_plan.requested_style or requested_style,
                    plan=semantic_plan,
                    semantic_state=semantic_state,
                    context=context,
                    resolution=semantic_resolution,
                    resolved_query=effective_query,
                    unsupported_reason=semantic_plan.unsupported_reason,
                )
            route = dict(rule)
        else:
            route = semantic_route_candidate(semantic_state) or dict(rule)
            semantic_plan.unsupported_reason = semantic_plan.unsupported_reason or "route_not_implemented"
            return finalize_route(
                route,
                intent=semantic_plan.intent or intent,
                requested_format=requested_format,
                requested_style=semantic_plan.requested_style or requested_style,
                plan=semantic_plan,
                semantic_state=semantic_state,
                context=context,
                resolved_query=effective_query,
                unsupported_reason=semantic_plan.unsupported_reason,
            )
    else:
        route = dict(rule)

    fallback_reason = "route_not_implemented" if route.get("mode") in {"summary", "analysis", "research"} else None
    plan = AnswerPlan(
        route=str(route.get("mode") or "analysis"),
        intent=intent,
        requested_style=requested_style,
        detail_level=detail_level_for_style(requested_style),
        context_reference=context.get("context_reference"),
        context_used=bool(context.get("context_used")),
        unsupported_reason=fallback_reason,
        confidence=float(route.get("confidence") or 0.0),
        parser="deterministic_fallback",
    )
    return finalize_route(
        route,
        intent=intent,
        requested_format=requested_format,
        requested_style=requested_style,
        plan=plan,
        semantic_state=semantic_state,
        context=context,
        resolved_query=effective_query,
        unsupported_reason=fallback_reason,
    )


def should_attempt_basic_lookup(query: str, *, route: dict[str, Any] | None = None) -> bool:
    route_data = route or route_query(query).to_dict()
    mode = str(route_data.get("mode") or "")
    signals = [str(signal) for signal in route_data.get("signals") or []]
    if mode in {"summary", "research", "chitchat", "unsupported", "source_reader"}:
        return False
    if mode == "analysis" and any(signal.startswith("relation:") for signal in signals):
        return False
    normalized = normalize_alias(query)
    return not contains_unsupported_answer_term(query)


def clarification_route(
    *,
    reason: str,
    query: str,
    requested_format: str,
    requested_style: str,
    context: dict[str, Any],
    model: str,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    route = {
        "mode": "unsupported",
        "confidence": 0.94,
        "signals": [f"clarification:{reason}"],
        "reason": clarification_reason_text(reason),
        "needs_clarification": True,
    }
    plan = AnswerPlan(
        route="unsupported",
        intent="clarification_required",
        requested_style=requested_style,
        detail_level=detail_level_for_style(requested_style),
        context_reference=context.get("context_reference"),
        context_used=bool(context.get("context_used")),
        needs_clarification=True,
        unsupported_reason=reason,
        confidence=float(route["confidence"]),
        parser="deterministic",
    )
    return finalize_route(
        route,
        intent="clarification_required",
        requested_format=requested_format,
        requested_style=requested_style,
        plan=plan,
        semantic_state=semantic_parse_state("", use_llm=False, model=model),
        context=context,
        resolution=resolution,
        resolved_query=query,
        unsupported_reason=reason,
    )


def clarification_reason_text(reason: str) -> str:
    if reason == "ambiguous_avatar_ascension":
        return "캐릭터 돌파효과 표현이 별자리, 특성, 돌파 보너스 중 무엇을 뜻하는지 모호합니다."
    if reason == "clarification_required_context":
        return "근거나 원문을 표시하려면 먼저 출처가 있는 답변이 필요합니다."
    return "정답형 조회에는 구체적인 성유물, 무기, 캐릭터 이름이 필요합니다."


def lookup_clarification_reason(query: str) -> str | None:
    if is_generic_category_lookup(query) or is_intent_only_lookup(query):
        return "clarification_required_entity"
    return None


def is_generic_category_lookup(query: str) -> bool:
    normalized = normalize_alias(query)
    if not any(normalize_alias(term) in normalized for term in GENERIC_LOOKUP_CATEGORY_TERMS):
        return False
    remainder = normalize_alias(strip_query_hints(query))
    return is_low_information_remainder(remainder)


def is_intent_only_lookup(query: str) -> bool:
    remainder = normalize_alias(strip_query_hints(query))
    for filler in FOLLOWUP_FILLER_TERMS:
        remainder = remainder.replace(normalize_alias(filler), "")
    remainder = strip_followup_suffixes(remainder)
    if is_low_information_remainder(remainder):
        return False
    intent_terms = {normalize_alias(term) for term in INTENT_ONLY_FOLLOWUP_TERMS if normalize_alias(term)}
    if remainder in intent_terms:
        return True
    return bool(re.fullmatch(r"c[1-6]", remainder.casefold()))


def is_ambiguous_avatar_ascension_query(query: str) -> bool:
    normalized = normalize_alias(query)
    has_ambiguous_ascension = any(normalize_alias(term) in normalized for term in ASCENSION_EFFECT_TERMS)
    if not has_ambiguous_ascension:
        return False
    explicit_terms = set(ASCENSION_BONUS_TERMS) | {"별자리", "운명의 자리", "운명의자리", "특성", "패시브", "C1", "C2", "C3", "C4", "C5", "C6"}
    return not any(normalize_alias(term) in normalized for term in explicit_terms if normalize_alias(term))


def is_low_information_remainder(value: str) -> bool:
    compact = normalize_alias(value)
    if compact in LOW_INFORMATION_REMAINDERS:
        return True
    return len(compact) <= 1


def followup_remainder(query: str, terms: set[str]) -> str:
    remainder = normalize_alias(query)
    for term in sorted({*terms, *FOLLOWUP_FILLER_TERMS}, key=len, reverse=True):
        normalized_term = normalize_alias(term)
        if normalized_term:
            remainder = remainder.replace(normalized_term, "")
    return strip_followup_suffixes(remainder)


def strip_followup_suffixes(value: str) -> str:
    text = normalize_alias(value).strip(" \t\r\n.!?？")
    changed = True
    while changed:
        changed = False
        for suffix in FOLLOWUP_SUFFIXES:
            normalized_suffix = normalize_alias(suffix)
            if normalized_suffix and text.endswith(normalized_suffix) and len(text) > len(normalized_suffix):
                text = text[: -len(normalized_suffix)].strip(" \t\r\n.!?？")
                changed = True
                break
    return text


def finalize_route(
    route: dict[str, Any],
    *,
    intent: str | None,
    requested_format: str,
    requested_style: str,
    plan: AnswerPlan,
    semantic_state: dict[str, Any],
    context: dict[str, Any],
    resolution: dict[str, Any] | None = None,
    resolved_query: str | None = None,
    unsupported_reason: str | None = None,
) -> dict[str, Any]:
    route.update(
        {
            "intent": intent,
            "requested_format": requested_format,
            "requested_style": requested_style,
            "semantic_parse": semantic_state,
            "answer_plan": plan.to_dict(),
            "parser": plan.parser,
            "context_reference": context.get("context_reference"),
            "context_used": bool(context.get("context_used")),
        }
    )
    if resolved_query:
        route["resolved_query"] = resolved_query
    if plan.needs_clarification:
        route["needs_clarification"] = True
    reason = unsupported_reason or plan.unsupported_reason
    if reason:
        route["unsupported_reason"] = reason
    if resolution:
        route["entities"] = entities_from_resolution(resolution)
        route["answer_plan"]["entities"] = entities_from_resolution(resolution)
    return route


def resolve_conversation_context(query: str, state: ConversationState | None) -> dict[str, Any]:
    if state is None:
        return {}
    active = state.active_entity or {}
    active_name = clean_text(str(active.get("name") or ""))
    normalized = normalize_alias(query)
    if not active_name:
        if is_context_only_source_followup(query) and state.last_sources:
            return {
                "route": "source_reader",
                "requested_style": source_reader_style_for_query(query),
                "context_reference": "last_answer",
                "context_used": True,
            }
        return {}
    if any(normalize_alias(term) in normalized for term in SOURCE_READER_TERMS) and (
        is_context_only_source_followup(query) or normalize_alias(active_name) in normalized
    ):
        source_style = source_reader_style_for_query(query)
        return {
            "route": "source_reader",
            "resolved_query": f"{active_name} {'원문' if source_style == 'raw' else '근거'}",
            "requested_style": source_style,
            "context_reference": "last_answer",
            "context_used": True,
        }
    if looks_like_story_summary(query) and active_name not in query:
        return {
            "route": "summary",
            "resolved_query": f"{active_name} 스토리 요약",
            "requested_style": "default",
            "context_reference": "last_entity",
            "context_used": True,
        }
    if is_intent_only_lookup(query):
        return {
            "route": "basic_lookup",
            "resolved_query": f"{active_name} {query}",
            "context_reference": "last_entity",
            "context_used": True,
        }
    if looks_like_brief_followup(query):
        return {
            "route": "basic_lookup",
            "resolved_query": f"{active_name} {query}",
            "requested_style": "brief",
            "context_reference": "last_entity",
            "context_used": True,
        }
    if looks_like_detail_followup(query):
        return {
            "route": "basic_lookup",
            "resolved_query": f"{active_name} {query}",
            "requested_style": "detail",
            "context_reference": "last_entity",
            "context_used": True,
        }
    return {}


def requested_style_for_query(query: str) -> str:
    normalized = normalize_alias(query)
    if any(normalize_alias(term) in normalized for term in RAW_STYLE_TERMS):
        return "raw"
    if any(normalize_alias(term) in normalized for term in EVIDENCE_STYLE_TERMS):
        return "evidence"
    if any(normalize_alias(term) in normalized for term in DETAIL_STYLE_TERMS):
        return "detail"
    if any(normalize_alias(term) in normalized for term in BRIEF_STYLE_TERMS) and not looks_like_story_summary(query):
        return "brief"
    return "default"


def detail_level_for_style(style: str) -> str:
    if style in {"detail", "raw", "research"}:
        return "high"
    if style == "brief":
        return "low"
    return "medium"


def looks_like_story_summary(query: str) -> bool:
    normalized = normalize_alias(query)
    has_story_scope = any(normalize_alias(term) in normalized for term in STORY_SUMMARY_TERMS)
    has_summary = any(normalize_alias(term) in normalized for term in BRIEF_STYLE_TERMS) or "알려줘" in normalized
    return has_story_scope and has_summary


def looks_like_detail_followup(query: str) -> bool:
    normalized = normalize_alias(query)
    if not any(normalize_alias(term) in normalized for term in DETAIL_STYLE_TERMS):
        return False
    return is_low_information_remainder(followup_remainder(query, set(DETAIL_STYLE_TERMS) | set(QUERY_HINTS)))


def looks_like_brief_followup(query: str) -> bool:
    normalized = normalize_alias(query)
    if not any(normalize_alias(term) in normalized for term in BRIEF_STYLE_TERMS):
        return False
    return is_low_information_remainder(followup_remainder(query, set(BRIEF_STYLE_TERMS) | set(QUERY_HINTS)))


def is_context_only_source_followup(query: str) -> bool:
    normalized = normalize_alias(query)
    if not any(normalize_alias(term) in normalized for term in SOURCE_READER_TERMS):
        return False
    return is_low_information_remainder(followup_remainder(query, SOURCE_READER_TERMS))


def source_reader_style_for_query(query: str) -> str:
    normalized = normalize_alias(query)
    if any(normalize_alias(term) in normalized for term in RAW_STYLE_TERMS):
        return "raw"
    return "evidence"


def summary_intent_for_query(query: str, resolution: dict[str, Any] | None) -> str:
    if resolution and resolution.get("content_type") == "avatar":
        return "character_story_summary"
    if "마신임무" in normalize_alias(query) or "퀘스트" in normalize_alias(query) or "임무" in normalize_alias(query):
        return "quest_summary"
    return "summary"


def entities_from_resolution(resolution: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not resolution:
        return []
    return [
        {
            "surface": resolution.get("title"),
            "name": resolution.get("title"),
            "canonical_id": resolution.get("canonical_id"),
            "content_type": resolution.get("content_type"),
            "confidence": 1.0,
        }
    ]


def contains_unsupported_answer_term(query: str) -> bool:
    normalized = normalize_alias(query)
    return any(normalize_alias(term) in normalized for term in UNSUPPORTED_ANSWER_TERMS)


def semantic_parse_state(query: str, *, use_llm: bool, model: str) -> dict[str, Any]:
    if not use_llm:
        return {"enabled": False, "ok": False, "parse": None, "error": None, "model": model}
    result = parse_query_semantics_with_ollama(query, model=model)
    result["enabled"] = True
    return result


def semantic_is_greeting(state: dict[str, Any]) -> bool:
    parse = state.get("parse") if isinstance(state, dict) else None
    return bool(isinstance(parse, dict) and (parse.get("is_greeting") or parse.get("route") == "chitchat"))


def semantic_route_candidate(state: dict[str, Any]) -> dict[str, Any] | None:
    parse = state.get("parse") if isinstance(state, dict) else None
    if not isinstance(parse, dict):
        return None
    route = str(parse.get("route") or "")
    if route not in {"basic_lookup", "summary", "analysis", "research"}:
        return None
    return {
        "mode": route,
        "confidence": max(0.5, float(parse.get("confidence") or 0.0)),
        "signals": [f"semantic:{route}"],
        "reason": parse.get("reason") or "LLM semantic parser 결과를 보조 라우팅 신호로 사용했습니다.",
    }


def unresolved_basic_lookup_route(route: dict[str, Any]) -> dict[str, Any]:
    if route.get("mode") != "basic_lookup":
        return route
    safe_route = dict(route)
    safe_route["mode"] = "analysis"
    safe_route["confidence"] = min(float(safe_route.get("confidence") or 0.0), 0.5)
    safe_route["signals"] = [*list(safe_route.get("signals") or []), "guard:unresolved_basic_lookup"]
    safe_route["reason"] = "정답형 조회로 확정할 수 있는 DB 엔티티가 없어 future-route 상태로 전환했습니다."
    safe_route["unsupported_reason"] = "route_not_implemented"
    plan_data = safe_route.get("answer_plan")
    if isinstance(plan_data, dict):
        safe_plan = dict(plan_data)
        safe_plan["route"] = "analysis"
        safe_plan["intent"] = safe_plan.get("intent") or safe_route.get("intent")
        safe_plan["unsupported_reason"] = "route_not_implemented"
        safe_route["answer_plan"] = safe_plan
    return safe_route


def requested_format_for_query(query: str) -> str:
    normalized = normalize_alias(query)
    if any(term in normalized for term in TABLE_FORMAT_TERMS):
        return "table"
    if any(term in normalized for term in STRUCTURED_FORMAT_TERMS):
        return "bullet"
    return "paragraph"


def classify_lookup_intent(query: str, resolution: dict[str, Any] | None) -> str | None:
    if not resolution:
        return None
    content_type = str(resolution.get("content_type") or "")
    normalized = normalize_alias(query)
    if content_type == "avatar":
        if any(term in normalized for term in CONSTELLATION_TERMS):
            return "character_constellation"
        if any(term in normalized for term in TALENT_TERMS):
            return "character_talent"
        return "character_basic_info"
    if content_type == "weapon":
        return "weapon_basic_info"
    if content_type == "reliquary":
        return "reliquary_effect_lookup"
    return None


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
        lexical_score = 0
        if title_norm in original_norm:
            lexical_score += len(title_norm) * 10
        if title_norm in query_norm:
            lexical_score += len(title_norm) * 12
        token_score = sum(1 for token in title.split() if normalize_alias(token) in original_norm)
        lexical_score += token_score * 4
        if lexical_score <= 0:
            continue
        score = lexical_score
        score += content_type_hint_score(query, str(row.get("content_type") or ""))
        scored.append((score, len(title_norm), row))
    if scored:
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return dict(scored[0][2])

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


def strip_query_hints(query: str) -> str:
    stripped = str(query)
    for hint in sorted(QUERY_HINTS, key=len, reverse=True):
        stripped = stripped.replace(hint, " ")
    return clean_text(stripped)


def content_type_hint_score(query: str, content_type: str) -> int:
    normalized = normalize_alias(query)
    if content_type == "reliquary" and ("성유물" in normalized or "효과" in normalized):
        return 8
    if content_type == "weapon" and ("무기" in normalized or "효과" in normalized):
        return 6
    if content_type == "avatar" and ("캐릭터" in normalized or "기본정보" in normalized):
        return 6
    return 0


def build_facts(raw_record: dict[str, Any], resolution: dict[str, Any], *, query: str = "") -> dict[str, Any]:
    payload = raw_record.get("payload") or {}
    source = source_from_raw(raw_record, resolution)
    content_type = str(resolution.get("content_type") or raw_record.get("metadata", {}).get("content_type") or "")
    if content_type == "reliquary":
        return build_reliquary_facts(payload, source=source)
    if content_type == "weapon":
        return build_weapon_facts(payload, source=source)
    if content_type == "avatar":
        intent = classify_lookup_intent(query, resolution) or "character_basic_info"
        return build_character_facts(payload, source=source, intent=intent)
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


def build_character_facts(
    payload: dict[str, Any],
    *,
    source: dict[str, Any],
    intent: str = "character_basic_info",
) -> dict[str, Any]:
    fetter = payload.get("fetter") or {}
    return {
        "intent": intent,
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
        "constellations": character_constellations(payload),
        "talents": character_talents(payload),
        "cv": fetter.get("cv") or {},
        "special_prop": prop_label(payload.get("specialProp")),
        "sources": [source],
    }


def character_constellations(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, value in sorted((payload.get("constellation") or {}).items(), key=lambda pair: sort_key(pair[0])):
        if not isinstance(value, dict):
            continue
        level = int(key) + 1 if str(key).isdigit() else key
        rows.append(
            {
                "level": level,
                "name": clean_text(value.get("name") or ""),
                "description": clean_text(value.get("description") or ""),
            }
        )
    return rows


def character_talents(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for key, value in sorted((payload.get("talent") or {}).items(), key=lambda pair: sort_key(pair[0])):
        if not isinstance(value, dict):
            continue
        name = clean_text(value.get("name") or "")
        description = clean_text(value.get("description") or "")
        if not name or not description:
            continue
        rows.append(
            {
                "id": str(key),
                "name": name,
                "description": description,
                "kind": talent_kind(str(key), name),
            }
        )
    return rows


def talent_kind(key: str, name: str) -> str:
    if key == "0":
        return "normal_attack"
    if key in {"1", "2"}:
        return "elemental_skill"
    if key == "3":
        return "elemental_burst"
    return "passive"


def sort_key(value: Any) -> tuple[int, str]:
    text = str(value)
    return (int(text), text) if text.isdigit() else (9999, text)


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


def draft_answer_from_facts(
    facts: dict[str, Any],
    *,
    requested_format: str = "paragraph",
    requested_style: str = "default",
) -> str:
    intent = facts.get("intent")
    if intent == "reliquary_effect_lookup":
        return draft_reliquary_answer(facts, requested_format=requested_format)
    if intent == "weapon_basic_info":
        return draft_weapon_answer(facts, requested_format=requested_format, requested_style=requested_style)
    if intent == "character_basic_info":
        return draft_character_answer(facts, requested_format=requested_format, requested_style=requested_style)
    if intent == "character_constellation":
        return draft_character_constellation_answer(facts, requested_format=requested_format)
    if intent == "character_talent":
        return draft_character_talent_answer(facts, requested_format=requested_format)
    return f"{facts.get('name') or '해당 항목'} 정보를 찾았습니다."


def draft_reliquary_answer(facts: dict[str, Any], *, requested_format: str) -> str:
    if requested_format == "table":
        rows = [["항목", "내용"], ["이름", facts["name"]], ["분류", "성유물 세트"]]
        rows.extend([format_effect_label(effect), effect["text"]] for effect in facts.get("effects") or [])
        if facts.get("acquisition"):
            rows.append(["획득처", ", ".join(facts["acquisition"])])
        rows.append(["출처", source_text(facts)])
        return markdown_table(rows)
    if requested_format == "bullet":
        lines = [f"{with_topic_particle(facts['name'])} 성유물 세트입니다."]
        for effect in facts.get("effects") or []:
            lines.append(f"- {format_effect_label(effect)}: {effect['text']}")
        piece_names = [piece["name"] for piece in facts.get("pieces") or [] if piece.get("name")]
        if piece_names:
            lines.append(f"- 구성 부위: {', '.join(piece_names)}")
        if facts.get("acquisition"):
            lines.append(f"- 획득처: {', '.join(facts['acquisition'])}")
        lines.append(source_line(facts))
        return "\n".join(lines)

    paragraphs = [f"{with_topic_particle(facts['name'])} 성유물 세트입니다."]
    for effect in facts.get("effects") or []:
        paragraphs.append(complete_korean_sentence(f"{format_effect_label(effect)} 효과는", str(effect["text"])))
    piece_names = [piece["name"] for piece in facts.get("pieces") or [] if piece.get("name")]
    if piece_names:
        paragraphs.append(f"구성 부위는 {', '.join(piece_names)}입니다.")
    if facts.get("acquisition"):
        paragraphs.append(f"획득처는 {', '.join(facts['acquisition'])}입니다.")
    paragraphs.append(source_text(facts))
    return "\n\n".join(paragraphs)


def draft_weapon_answer(facts: dict[str, Any], *, requested_format: str, requested_style: str = "default") -> str:
    include_all_refinements = requested_style in {"detail", "raw"} or requested_format == "table"
    if requested_format == "table":
        rows = [
            ["항목", "내용"],
            ["이름", facts["name"]],
            ["등급/종류", f"{facts.get('rank')}성 {facts.get('weapon_type')}"],
        ]
        if facts.get("special_prop"):
            rows.append(["보조 속성", facts["special_prop"]])
        for affix in facts.get("affixes") or []:
            rows.append(["무기 효과", affix.get("name") or affix.get("id")])
            for refinement in affix.get("refinements") or []:
                rows.append([f"R{refinement['level']}", refinement["text"]])
            break
        rows.append(["출처", source_text(facts)])
        return markdown_table(rows)

    if requested_format == "bullet":
        lines = [f"{with_topic_particle(facts['name'])} {facts.get('rank')}성 {facts.get('weapon_type')}입니다."]
        if facts.get("description"):
            lines.append(f"- 설명: {facts['description']}")
        if facts.get("special_prop"):
            lines.append(f"- 보조 속성: {facts['special_prop']}")
        for affix in facts.get("affixes") or []:
            lines.append(f"- 무기 효과: {affix.get('name') or affix.get('id')}")
            refinements = affix.get("refinements") or []
            if refinements:
                lines.append("- 효과 수치는 제련 단계에 따라 증가합니다.")
                shown_refinements = refinements if include_all_refinements else refinements[:1]
                for refinement in shown_refinements:
                    lines.append(f"  - R{refinement['level']}: {refinement['text']}")
                if not include_all_refinements and len(refinements) > 1:
                    lines.append("- R2~R5 수치는 제련별 또는 자세히 요청하면 펼쳐볼 수 있습니다.")
            break
        lines.append(source_line(facts))
        return "\n".join(lines)

    paragraphs = [f"{with_topic_particle(facts['name'])} {facts.get('rank')}성 {facts.get('weapon_type')}입니다."]
    if facts.get("description"):
        paragraphs.append(complete_korean_sentence("설명은", str(facts["description"])))
    if facts.get("special_prop"):
        paragraphs.append(f"보조 속성은 {facts['special_prop']}입니다.")
    for affix in facts.get("affixes") or []:
        effect_lines = [f"무기 효과는 {affix.get('name') or affix.get('id')}입니다."]
        refinements = affix.get("refinements") or []
        if refinements:
            effect_lines.append("효과 수치는 제련 단계에 따라 증가합니다.")
            shown_refinements = refinements if include_all_refinements else refinements[:1]
            effect_lines.extend(f"R{refinement['level']}: {refinement['text']}" for refinement in shown_refinements)
            if not include_all_refinements and len(refinements) > 1:
                effect_lines.append("R2~R5 수치는 제련별 또는 자세히 요청하면 펼쳐볼 수 있습니다.")
        paragraphs.append("\n".join(effect_lines))
        break
    paragraphs.append(source_text(facts))
    return "\n\n".join(paragraphs)


def draft_character_answer(facts: dict[str, Any], *, requested_format: str, requested_style: str = "default") -> str:
    if requested_format == "table":
        rows = [["항목", "내용"], ["이름", facts["name"]], ["등급", f"{facts.get('rank')}성"]]
        for key, label in character_basic_fields():
            if facts.get(key):
                rows.append([label, str(facts[key])])
        rows.append(["출처", source_text(facts)])
        return markdown_table(rows)

    if requested_format == "bullet":
        lines = [f"{with_topic_particle(facts['name'])} {facts.get('rank')}성 캐릭터입니다."]
        for key, label in character_basic_fields():
            if facts.get(key):
                lines.append(f"- {label}: {facts[key]}")
        if facts.get("cv"):
            parts = [f"{lang}: {name}" for lang, name in sorted(facts["cv"].items()) if name]
            if parts:
                lines.append(f"- CV: {', '.join(parts)}")
        lines.append(source_line(facts))
        return "\n".join(lines)

    first_bits = []
    if facts.get("region"):
        first_bits.append(f"{facts['region']} 출신의")
    if facts.get("rank"):
        first_bits.append(f"{facts['rank']}성")
    if facts.get("element"):
        first_bits.append(f"{facts['element']} 원소")
    first = f"{with_topic_particle(facts['name'])} {' '.join(first_bits)} 캐릭터입니다.".replace("  ", " ")
    paragraphs = [first]
    details = []
    if facts.get("weapon_type"):
        details.append(f"무기는 {with_object_particle(facts['weapon_type'])} 사용합니다")
    if facts.get("constellation"):
        details.append(f"운명의 자리는 {facts['constellation']}입니다")
    if facts.get("birthday"):
        details.append(f"생일은 {facts['birthday']}로 기록되어 있습니다")
    if facts.get("special_prop"):
        details.append(f"돌파 보너스는 {facts['special_prop']}입니다")
    if details:
        paragraphs.append(". ".join(details) + ".")
    if requested_style == "brief":
        paragraphs.append(source_text(facts))
        return "\n\n".join(paragraphs)
    if facts.get("title"):
        paragraphs.append(f"칭호는 {facts['title']}입니다.")
    if facts.get("detail"):
        paragraphs.append(f"소개문에는 {with_quote_particle(facts['detail'])} 적혀 있습니다.")
    if facts.get("cv"):
        parts = [f"{lang}: {name}" for lang, name in sorted(facts["cv"].items()) if name]
        if parts:
            paragraphs.append(f"CV는 {', '.join(parts)}입니다.")
    paragraphs.append(source_text(facts))
    return "\n\n".join(paragraphs)


def draft_character_constellation_answer(facts: dict[str, Any], *, requested_format: str) -> str:
    rows = facts.get("constellations") or []
    if requested_format == "table":
        table_rows = [["단계", "이름", "효과"]]
        table_rows.extend([f"C{row['level']}", row.get("name") or "", row.get("description") or ""] for row in rows)
        table_rows.append(["출처", source_text(facts), ""])
        return markdown_table(table_rows)
    lines = [f"{facts['name']}의 별자리 효과입니다."]
    for row in rows:
        lines.append(f"C{row['level']} {row.get('name')}: {row.get('description')}")
    lines.append(source_text(facts))
    return "\n\n".join([lines[0], "\n".join(lines[1:-1]), lines[-1]])


def draft_character_talent_answer(facts: dict[str, Any], *, requested_format: str) -> str:
    rows = facts.get("talents") or []
    if requested_format == "table":
        table_rows = [["구분", "이름", "설명"]]
        table_rows.extend([talent_kind_label(row.get("kind")), row.get("name") or "", row.get("description") or ""] for row in rows)
        table_rows.append(["출처", source_text(facts), ""])
        return markdown_table(table_rows)
    lines = [f"{facts['name']}의 특성 정보입니다."]
    for row in rows:
        lines.append(f"{talent_kind_label(row.get('kind'))} - {row.get('name')}: {row.get('description')}")
    lines.append(source_text(facts))
    return "\n\n".join([lines[0], "\n".join(lines[1:-1]), lines[-1]])


def source_line(facts: dict[str, Any]) -> str:
    return f"- {source_text(facts)}"


def source_text(facts: dict[str, Any]) -> str:
    source = (facts.get("sources") or [{}])[0]
    return f"출처: {source.get('source') or 'project_amber'} 공식 데이터 ({source.get('language') or 'ko'})"


def format_effect_label(effect: dict[str, Any]) -> str:
    return f"{effect['pieces']}세트" if effect.get("pieces") else str(effect.get("id") or "효과")


def character_basic_fields() -> list[tuple[str, str]]:
    return [
        ("element", "원소"),
        ("weapon_type", "무기"),
        ("region", "지역"),
        ("birthday", "생일"),
        ("constellation", "운명의 자리"),
        ("special_prop", "돌파 보너스"),
        ("title", "칭호"),
        ("detail", "소개"),
    ]


def talent_kind_label(kind: Any) -> str:
    return {
        "normal_attack": "일반 공격",
        "elemental_skill": "원소전투 스킬",
        "elemental_burst": "원소폭발",
        "passive": "패시브",
    }.get(str(kind), "특성")


def markdown_table(rows: list[list[Any]]) -> str:
    if not rows:
        return ""
    escaped = [[table_cell(value) for value in row] for row in rows]
    width = max(len(row) for row in escaped)
    padded = [row + [""] * (width - len(row)) for row in escaped]
    header = "| " + " | ".join(padded[0]) + " |"
    divider = "| " + " | ".join("---" for _ in range(width)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in padded[1:]]
    return "\n".join([header, divider, *body])


def table_cell(value: Any) -> str:
    return clean_text(str(value or "")).replace("|", "\\|").replace("\n", "<br>")


def with_topic_particle(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    return append_korean_particle(text, "은", "는")


def with_object_particle(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    return append_korean_particle(text, "을", "를")


def with_quote_particle(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    if text.endswith("다"):
        return text[:-1] + "다고"
    return append_korean_particle(text, "이라고", "라고")


def append_korean_particle(text: str, consonant_particle: str, vowel_particle: str) -> str:
    last = text[-1]
    return text + (consonant_particle if has_korean_final_consonant(last) else vowel_particle)


def has_korean_final_consonant(value: str) -> bool:
    if not value:
        return False
    code = ord(value[-1])
    if 0xAC00 <= code <= 0xD7A3:
        return (code - 0xAC00) % 28 != 0
    return False


def complete_korean_sentence(prefix: str, text: str) -> str:
    clause = clean_text(text)
    if not clause:
        return prefix.strip()
    if clause.endswith((".", "!", "?")):
        return f"{prefix} {clause}"
    if looks_like_complete_korean_sentence(clause):
        return f"{prefix} {clause}."
    return f"{prefix} {clause}입니다."


def looks_like_complete_korean_sentence(text: str) -> bool:
    return text.endswith(("다", "요", "함", "음"))


def validate_answer(
    answer: str,
    facts: dict[str, Any],
    draft_answer: str,
    *,
    requested_style: str = "default",
) -> dict[str, Any]:
    reasons = []
    cleaned = clean_text(answer)
    if not cleaned:
        reasons.append("empty_answer")
    primary_name = str(facts.get("name") or "").strip()
    if primary_name and primary_name not in cleaned:
        reasons.append(f"missing_primary_name:{primary_name}")
    draft_cleaned = clean_text(draft_answer)
    max_rewrite_length = max(int(len(draft_cleaned) * 1.65), len(draft_cleaned) + 60)
    if draft_cleaned and len(cleaned) > max_rewrite_length:
        reasons.append("answer_too_long")
    if draft_cleaned and compact_for_presence(cleaned).count(compact_for_presence(draft_cleaned)) > 1:
        reasons.append("repeated_draft")
    if primary_name and cleaned.count(primary_name) > draft_cleaned.count(primary_name) + 1:
        reasons.append(f"repeated_primary_name:{primary_name}")

    missing_fragments = [
        fragment
        for fragment in required_fact_fragments(facts, requested_style=requested_style)
        if compact_for_presence(fragment) not in compact_for_presence(cleaned)
    ]
    if missing_fragments:
        reasons.append("missing_fact_fragments:" + ",".join(missing_fragments[:5]))

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

    wrong_type_phrases = type_phrase_violations(cleaned, facts)
    if wrong_type_phrases:
        reasons.extend(wrong_type_phrases)

    return {
        "ok": not reasons,
        "reasons": reasons,
        "reason_codes": [reason.split(":", 1)[0] for reason in reasons],
    }


def required_fact_fragments(facts: dict[str, Any], *, requested_style: str = "default") -> list[str]:
    fragments = []
    intent = facts.get("intent")
    rank = facts.get("rank")
    weapon_type = facts.get("weapon_type")
    if intent == "weapon_basic_info" and rank and weapon_type:
        fragments.append(f"{rank}성 {weapon_type}")
    if intent == "character_basic_info" and rank:
        fragments.append(f"{rank}성")
        fragments.append("캐릭터")
    for effect in facts.get("effects") or []:
        if effect.get("text"):
            fragments.append(str(effect["text"]))
    for value in facts.get("acquisition") or []:
        if value:
            fragments.append(str(value))
    for affix in facts.get("affixes") or []:
        if affix.get("name"):
            fragments.append(str(affix["name"]))
        refinements = affix.get("refinements") or []
        required_refinements = refinements if requested_style in {"detail", "raw"} else refinements[:1]
        for refinement in required_refinements:
            if refinement.get("text"):
                fragments.append(str(refinement["text"]))
    if intent == "character_basic_info":
        skipped_brief_fields = {"title", "detail"} if requested_style == "brief" else set()
        for key, _label in character_basic_fields():
            if key in skipped_brief_fields:
                continue
            if facts.get(key):
                fragments.append(str(facts[key]))
    elif intent == "character_constellation":
        for row in facts.get("constellations") or []:
            if row.get("name"):
                fragments.append(str(row["name"]))
            if row.get("description"):
                fragments.append(str(row["description"]))
    elif intent == "character_talent":
        for row in facts.get("talents") or []:
            if row.get("name"):
                fragments.append(str(row["name"]))
            if row.get("description"):
                fragments.append(str(row["description"]))
    else:
        for key in [
            "weapon_type",
            "description",
            "special_prop",
        ]:
            if facts.get(key):
                fragments.append(str(facts[key]))
    if facts.get("sources"):
        fragments.append(source_text(facts))
    return fragments


def type_phrase_violations(answer: str, facts: dict[str, Any]) -> list[str]:
    content_type = str(facts.get("content_type") or "")
    phrase_rules = {
        "avatar": {
            "avatar_as_reliquary": ["성유물 세트"],
            "avatar_as_weapon": ["한손검입니다", "양손검입니다", "장병기입니다", "활입니다", "법구입니다", "무기입니다"],
        },
        "weapon": {
            "weapon_as_reliquary": ["성유물 세트"],
            "weapon_as_avatar": ["캐릭터입니다", "원소 캐릭터"],
        },
        "reliquary": {
            "reliquary_as_weapon": ["한손검입니다", "양손검입니다", "장병기입니다", "활입니다", "법구입니다", "무기입니다"],
            "reliquary_as_avatar": ["캐릭터입니다", "원소 캐릭터"],
        },
    }
    violations = []
    for code, phrases in phrase_rules.get(content_type, {}).items():
        for phrase in phrases:
            if phrase in answer:
                violations.append(f"wrong_type_phrase:{code}:{phrase}")
    return violations


def compact_for_presence(text: str) -> str:
    return re.sub(r"\s+", "", clean_text(text))


def extract_numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?%?", text))


def extract_quoted_names(text: str) -> list[str]:
    rows = []
    rows.extend(re.findall(r"「([^」]{1,40})」", text))
    rows.extend(re.findall(r'"([^"]{1,40})"', text))
    return [clean_text(row) for row in rows]


def small_talk_answer(query: str, db_path: Path, *, route: dict[str, Any]) -> dict[str, Any]:
    message = "안녕하세요. 현재는 성유물, 무기, 캐릭터 공식 데이터 조회를 지원합니다. 궁금한 항목 이름을 입력해 주세요."
    return {
        "query": query,
        "canonical_id": None,
        "content_type": None,
        "item_id": None,
        "intent": "small_talk",
        "facts": {},
        "draft_answer": message,
        "final_answer": message,
        "llm": {
            "enabled": False,
            "used": False,
            "model": DEFAULT_OLLAMA_MODEL,
            "ok": False,
            "error": None,
        },
        "validation": {"ok": True, "reasons": []},
        "sources": [{"db_path": str(db_path)}],
        "route": route,
        "requested_format": route.get("requested_format") or "paragraph",
        "requested_style": route.get("requested_style") or "default",
        "answer_plan": route.get("answer_plan"),
        "semantic_parse": route.get("semantic_parse"),
    }


def evidence_answer(
    query: str,
    db_path: Path,
    *,
    route: dict[str, Any],
    conversation_state: ConversationState | None,
) -> dict[str, Any]:
    sources = list(conversation_state.last_sources) if conversation_state and conversation_state.last_sources else []
    if not sources:
        sources = [{"db_path": str(db_path)}]
    lines = ["직전 답변의 근거로 저장된 출처 metadata를 표시합니다."]
    for index, source in enumerate(sources, start=1):
        source_name = source.get("source") or "project_amber"
        language = source.get("language") or "ko"
        raw_ref = source.get("raw_ref") or source.get("db_path")
        source_url = source.get("source_url")
        detail = f"{index}. 출처: {source_name} 공식 데이터 ({language})"
        if raw_ref:
            detail += f" / raw_ref: {raw_ref}"
        if source_url:
            detail += f" / source_url: {source_url}"
        lines.append(detail)
    lines.append("Source Reader 본문 재인용은 아직 Evidence Pack 통합 전 단계입니다.")
    message = "\n".join(lines)
    return {
        "query": query,
        "canonical_id": None,
        "content_type": None,
        "item_id": None,
        "intent": "show_evidence",
        "facts": {},
        "draft_answer": message,
        "final_answer": message,
        "llm": {
            "enabled": False,
            "used": False,
            "model": DEFAULT_OLLAMA_MODEL,
            "ok": False,
            "error": None,
        },
        "validation": {"ok": True, "reasons": []},
        "sources": sources,
        "route": route,
        "requested_format": route.get("requested_format") or requested_format_for_query(query),
        "requested_style": route.get("requested_style") or "evidence",
        "answer_plan": route.get("answer_plan"),
        "semantic_parse": route.get("semantic_parse"),
    }


def unsupported_answer(query: str, db_path: Path, *, route: dict[str, Any] | None = None) -> dict[str, Any]:
    route = route or route_query(query).to_dict()
    message = unsupported_message(route)
    return {
        "query": query,
        "canonical_id": None,
        "content_type": None,
        "item_id": None,
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
        "route": route,
        "requested_format": route.get("requested_format") or requested_format_for_query(query),
        "requested_style": route.get("requested_style") or requested_style_for_query(query),
        "answer_plan": route.get("answer_plan"),
        "semantic_parse": route.get("semantic_parse"),
    }


def unsupported_message(route: dict[str, Any]) -> str:
    reason = str(route.get("unsupported_reason") or "")
    if reason == "unofficial_strategy_request":
        return (
            "지원하는 정답형 QA 대상이 아닙니다. 현재 시스템은 공식 데이터 조회와 근거 확인만 지원하며, "
            "플레이 조언이나 메타 평가는 답변하지 않습니다. "
            "성유물 효과, 무기 정보, 캐릭터 기본정보처럼 공식 데이터 항목으로 물어봐 주세요."
        )
    if reason == "clarification_required_context":
        return "직전 답변의 근거나 원문을 보려면 먼저 성유물, 무기, 캐릭터 공식 데이터 항목을 조회해 주세요."
    if reason == "clarification_required_entity":
        return (
            "구체적인 이름을 입력해 주세요. 예: 절연의 기치 효과, 안개를 가르는 회광 정보, "
            "아야카 별자리처럼 성유물, 무기, 캐릭터 이름을 함께 써야 합니다."
        )
    if reason == "ambiguous_avatar_ascension":
        return (
            "캐릭터의 돌파효과는 의미가 모호합니다. 돌파 보너스를 원하면 '돌파 보너스', "
            "운명의 자리를 원하면 '별자리', 스킬/패시브를 원하면 '특성'이라고 써 주세요."
        )
    return "지원하는 정답형 QA 대상을 찾지 못했습니다. 현재는 성유물, 무기, 캐릭터 기본정보를 지원합니다."
