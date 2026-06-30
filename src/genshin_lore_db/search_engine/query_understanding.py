from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from genshin_lore_db.io import read_json
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.pipeline.project_amber_v2 import search_project_amber_v2
from genshin_lore_db.search_engine.aliases import normalize_alias
from genshin_lore_db.search_engine.conversation import ConversationState, is_source_context
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, ollama_chat
from genshin_lore_db.search_engine.router import is_greeting_query
from genshin_lore_db.search_engine.semantic import parse_semantic_response


QUERY_UNDERSTANDING_VERSION = "query_understanding.v0.1"
CANDIDATE_PACK_VERSION = "candidate_meaning_pack.v0.1"
DEFAULT_LANGUAGE = "ko"

SUPPORTED_CONTENT_TYPES = {"avatar", "weapon", "reliquary"}
SUPPORTED_ROUTES = {"basic_lookup", "summary", "analysis", "research", "source_reader", "chitchat", "unsupported"}

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
SOURCE_READER_TERMS = {"근거", "출처", "source", "evidence", "원문", "raw", "RAW", "그대로"}
RAW_STYLE_TERMS = {"원문", "raw", "RAW", "그대로"}
STORY_SCOPE_TERMS = {"스토리", "줄거리", "마신임무", "임무", "퀘스트", "전설임무", "내용"}
SUMMARY_TERMS = {"요약", "간단", "간단히", "짧게", "핵심만", "줄거리"}
DETAIL_TERMS = {"자세히", "전체", "전부", "R1", "R2", "R3", "R4", "R5", "r1", "r2", "r3", "r4", "r5", "제련", "재련", "제련별", "재련별", "수치"}
INTENT_ONLY_TERMS = {"별자리", "운명의자리", "운명의 자리", "특성", "스킬", "패시브", "제련", "재련", "제련별", "재련별", "수치"}
FOLLOWUP_FILLER_TERMS = {"더", "좀", "부터", "까지", "보여줘", "알려줘", "해줘", "효과", "는", "은", "이", "가", "을", "를", "도"}
LOW_INFORMATION_REMAINDERS = {"", "에", "에대해", "에대해서", "의", "은", "는", "을", "를", "가", "이", "도", "좀"}
REGION_TERMS = {
    "몬드": "mondstadt",
    "리월": "liyue",
    "이나즈마": "inazuma",
    "수메르": "sumeru",
    "폰타인": "fontaine",
    "나타": "natlan",
    "스네즈나야": "snezhnaya",
    "켄리아": "khaenriah",
    "카엔리아": "khaenriah",
}


def understand_query(
    root: Path | str,
    query: str,
    *,
    db_path: Path,
    language: str = DEFAULT_LANGUAGE,
    conversation_state: ConversationState | None = None,
    use_llm: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    conversation_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    db_path = Path(db_path).resolve()
    normalized_query = normalize_alias(query)
    stripped_query = strip_query_hints(query)
    context_summary = conversation_context_summary(query, conversation_state, conversation_context)

    candidates: list[dict[str, Any]] = []
    candidates.extend(chitchat_candidates(query))
    candidates.extend(unsupported_candidates(query))
    candidates.extend(source_followup_candidates(query, conversation_state))
    candidates.extend(followup_candidates(query, conversation_state, conversation_context))
    candidates.extend(lore_concept_candidates(root_path, query, db_path=db_path, language=language))
    candidates.extend(story_scope_candidates(query))
    candidates.extend(supported_entity_candidates(db_path, query, language=language))
    candidates.extend(source_search_candidates(db_path, query, language=language))
    candidates = dedupe_candidates(candidates)
    mark_supported_conflicts(candidates)
    if not candidates:
        candidates = [unknown_candidate(query)]

    deterministic = select_deterministic_candidate(candidates, query=query)
    llm_state = adjudicate_with_llm(query, candidates, deterministic, use_llm=use_llm, model=model)
    selected, fallback_used = validate_llm_selection(llm_state, candidates, deterministic)

    return {
        "schema_version": QUERY_UNDERSTANDING_VERSION,
        "candidate_pack_schema_version": CANDIDATE_PACK_VERSION,
        "query": query,
        "normalized_query": normalized_query,
        "stripped_query": stripped_query,
        "db_path": str(db_path),
        "language": language,
        "conversation_context": context_summary,
        "candidates": candidates,
        "selected_candidate_id": selected.get("id"),
        "selected_candidate": selected,
        "selected_meaning": {
            "candidate_id": selected.get("id"),
            "kind": selected.get("kind"),
            "surface": selected.get("surface"),
            "route": selected.get("route_candidate"),
            "match_strength": selected.get("match_strength"),
            "supported_for_current_writer": selected.get("kind") == "supported_entity"
            and selected.get("match_strength") == "strong",
        },
        "route_candidate": selected.get("route_candidate"),
        "llm_adjudication": llm_state,
        "fallback_used": fallback_used,
    }


def chitchat_candidates(query: str) -> list[dict[str, Any]]:
    if not is_greeting_query(query):
        return []
    return [
        candidate(
            "guard:chitchat",
            "unknown_or_low_information",
            surface=query,
            route_candidate="chitchat",
            confidence=0.98,
            match_strength="strong",
            match_reasons=["guard:greeting"],
        )
    ]


def unsupported_candidates(query: str) -> list[dict[str, Any]]:
    normalized = normalize_alias(query)
    hits = [term for term in UNSUPPORTED_ANSWER_TERMS if normalize_alias(term) in normalized]
    if not hits:
        return []
    return [
        candidate(
            "unsupported:gameplay_meta",
            "gameplay_or_meta_unsupported",
            surface=", ".join(sorted(hits)),
            route_candidate="unsupported",
            confidence=0.96,
            match_strength="strong",
            match_reasons=[f"unsupported_term:{term}" for term in sorted(hits)],
            risk_flags=["outside_current_official_db_qa_scope"],
        )
    ]


def source_followup_candidates(query: str, state: ConversationState | None) -> list[dict[str, Any]]:
    if not is_context_only_source_followup(query):
        return []
    has_sources = bool(state and any(is_source_context(source) for source in state.last_sources))
    return [
        candidate(
            "followup:source_reader",
            "source_or_evidence_request",
            surface=query,
            route_candidate="source_reader" if has_sources else "unsupported",
            confidence=0.9 if has_sources else 0.86,
            match_strength="strong",
            match_reasons=["context_only_source_followup"],
            risk_flags=[] if has_sources else ["missing_prior_source_context"],
            source_refs=source_refs_from_state(state) if has_sources else [],
            source_readable=has_sources,
            context_used=has_sources,
        )
    ]


def followup_candidates(
    query: str,
    state: ConversationState | None,
    conversation_context: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if state is None:
        return []
    active = state.active_entity or {}
    active_name = clean_text(str(active.get("name") or ""))
    if not active_name:
        return []
    explicit_topic = has_explicit_topic_signal(query)
    if explicit_topic and not is_low_information_followup(query):
        return [
            candidate(
                "followup:context_rejected_explicit_topic",
                "followup_request",
                surface=active_name,
                canonical_id=str(active.get("canonical_id") or "") or None,
                content_type=str(active.get("content_type") or "") or None,
                route_candidate="analysis",
                confidence=0.35,
                match_strength="weak",
                match_reasons=["prior_context_available_but_query_has_explicit_topic"],
                risk_flags=["context_rejected_explicit_topic"],
                context_used=False,
            )
        ]
    if not is_low_information_followup(query) and not (conversation_context or {}).get("context_used"):
        return []
    route_candidate = str((conversation_context or {}).get("route") or "")
    if not route_candidate:
        route_candidate = "summary" if looks_like_story_scope(query) else "basic_lookup"
    return [
        candidate(
            "followup:last_entity",
            "followup_request",
            surface=active_name,
            canonical_id=str(active.get("canonical_id") or "") or None,
            content_type=str(active.get("content_type") or "") or None,
            route_candidate=route_candidate,
            confidence=0.82,
            match_strength="strong",
            match_reasons=["low_information_followup_uses_last_entity"],
            context_used=True,
        )
    ]


def lore_concept_candidates(root: Path, query: str, *, db_path: Path, language: str) -> list[dict[str, Any]]:
    concepts = load_lore_concepts(root)
    query_norm = normalize_alias(query)
    stripped_norm = normalize_alias(strip_query_hints(query))
    rows = []
    for concept in concepts:
        best: dict[str, Any] | None = None
        for alias in concept_aliases(concept):
            alias_norm = normalize_alias(alias.get("name") or "")
            if not alias_norm:
                continue
            strength, score, reasons, risks = lore_alias_match(alias_norm, query_norm, stripped_norm)
            if strength is None:
                continue
            item = candidate(
                f"concept:{concept['concept_id']}",
                "lore_concept",
                surface=str(concept.get("primary_name") or alias.get("name") or concept.get("concept_id")),
                concept_id=str(concept.get("concept_id") or ""),
                route_candidate="analysis",
                confidence=score,
                score=score,
                match_strength=strength,
                match_reasons=[*reasons, f"alias:{alias.get('name')}"],
                risk_flags=risks,
                supporting_hits=concept_supporting_hits(db_path, str(alias.get("name") or ""), language=language),
            )
            item["source_readable"] = any(ref.get("unit_id") for ref in item.get("source_refs") or [])
            if best is None or candidate_sort_key(item, query=query) > candidate_sort_key(best, query=query):
                best = item
        if best:
            rows.append(best)
    return rows


def story_scope_candidates(query: str) -> list[dict[str, Any]]:
    normalized = normalize_alias(query)
    story_hits = [term for term in STORY_SCOPE_TERMS if normalize_alias(term) in normalized]
    summary_hits = [term for term in SUMMARY_TERMS if normalize_alias(term) in normalized]
    region_hits = [name for name in REGION_TERMS if normalize_alias(name) in normalized]
    if not story_hits and not summary_hits and not region_hits:
        return []
    if summary_hits and not story_hits and not region_hits:
        return []
    route_candidate = "summary" if looks_like_story_scope(query) else "analysis"
    strength = "strong" if story_hits or summary_hits else "weak"
    return [
        candidate(
            "scope:story_or_region",
            "region_or_story_scope",
            surface=clean_text(" ".join([*region_hits, *story_hits, *summary_hits])) or query,
            route_candidate=route_candidate,
            confidence=0.82 if strength == "strong" else 0.58,
            match_strength=strength,
            match_reasons=[*(f"region:{term}" for term in region_hits), *(f"story_scope:{term}" for term in story_hits), *(f"summary:{term}" for term in summary_hits)],
        )
    ]


def supported_entity_candidates(db_path: Path, query: str, *, language: str) -> list[dict[str, Any]]:
    rows = supported_title_rows(db_path, language=language)
    query_norm = normalize_alias(strip_query_hints(query))
    original_norm = normalize_alias(query)
    candidates = []
    for row in rows:
        title = str(row.get("title") or "")
        title_norm = normalize_alias(title)
        if not title_norm:
            continue
        strength, score, reasons, risks = supported_match_score(
            title=title,
            title_norm=title_norm,
            query_norm=query_norm,
            original_norm=original_norm,
            query=query,
            content_type=str(row.get("content_type") or ""),
        )
        if strength is None:
            continue
        candidates.append(
            candidate(
                f"supported:{row.get('canonical_id')}",
                "supported_entity",
                surface=title,
                canonical_id=str(row.get("canonical_id") or ""),
                content_type=str(row.get("content_type") or ""),
                route_candidate="basic_lookup" if strength == "strong" else "analysis",
                confidence=score,
                score=score,
                match_strength=strength,
                match_reasons=reasons,
                risk_flags=risks,
                source_refs=[source_ref_from_resolution(row)],
                source_readable=bool(row.get("raw_ref") or row.get("source_url")),
                resolution=dict(row),
            )
        )
    return candidates


def source_search_candidates(db_path: Path, query: str, *, language: str) -> list[dict[str, Any]]:
    hits = safe_search(db_path, query, language=language, limit=5, include_textmap=True)
    candidates = []
    for index, hit in enumerate(hits):
        source_ref = source_ref_from_hit(hit)
        result_type = str(hit.get("result_type") or "")
        content_type = str(hit.get("content_type") or "")
        source_readable = result_type == "text_unit" and bool(hit.get("unit_id"))
        story_query = looks_like_story_scope(query)
        kind = "quest_or_book_scope" if content_type in {"quest", "book"} else "unknown_or_low_information"
        match_strength = "strong" if story_query and kind == "quest_or_book_scope" and source_readable else "weak"
        risks = []
        if result_type == "textmap":
            risks.append("textmap_only_not_source_readable")
            source_readable = False
        candidates.append(
            candidate(
                f"source_search:{source_ref.get('result_type') or 'result'}:{source_ref.get('unit_id') or source_ref.get('textmap_id') or index}",
                kind,
                surface=str(hit.get("title") or hit.get("text") or query)[:120],
                canonical_id=str(hit.get("canonical_id") or "") or None,
                content_type=content_type or None,
                route_candidate="summary" if story_query and kind == "quest_or_book_scope" else "analysis",
                confidence=0.68 if match_strength == "strong" else 0.42,
                score=hit.get("score"),
                match_strength=match_strength,
                match_reasons=[f"source_search:{result_type or 'unknown'}"],
                risk_flags=risks,
                supporting_hits=[source_ref],
                source_readable=source_readable,
            )
        )
    return candidates


def select_deterministic_candidate(candidates: list[dict[str, Any]], *, query: str) -> dict[str, Any]:
    return max(candidates, key=lambda item: candidate_sort_key(item, query=query))


def candidate_sort_key(item: dict[str, Any], *, query: str) -> tuple[int, int, float, float]:
    if item.get("id") == "guard:chitchat":
        return (112, 3, float(item.get("confidence") or 0.0), float(item.get("score") or 0.0))
    kind = str(item.get("kind") or "")
    strength = str(item.get("match_strength") or "")
    story_query = looks_like_story_scope(query)
    priority = {
        "gameplay_or_meta_unsupported": 110,
        "source_or_evidence_request": 105,
        "followup_request": 100 if item.get("context_used") else 90,
        "supported_entity": 82,
        "lore_concept": 80,
        "region_or_story_scope": 76,
        "quest_or_book_scope": 74,
        "unknown_or_low_information": 10,
    }.get(kind, 0)
    if story_query and kind in {"region_or_story_scope", "quest_or_book_scope"}:
        priority += 20
    if kind == "supported_entity" and strength != "strong":
        priority -= 18
    if strength == "unsafe":
        priority -= 70
    strength_rank = {"strong": 3, "weak": 2, "unsafe": 1}.get(strength, 0)
    return (priority, strength_rank, float(item.get("confidence") or 0.0), float(item.get("score") or 0.0))


def adjudicate_with_llm(
    query: str,
    candidates: list[dict[str, Any]],
    deterministic: dict[str, Any],
    *,
    use_llm: bool,
    model: str,
) -> dict[str, Any]:
    state: dict[str, Any] = {
        "enabled": use_llm,
        "used": False,
        "model": model,
        "ok": False,
        "valid": False,
        "selected_candidate_id": None,
        "route": None,
        "confidence": None,
        "reason": None,
        "uncertainty": [],
        "needs_more_evidence": False,
        "error": None,
    }
    if not use_llm:
        return state
    if not should_use_llm(candidates, deterministic):
        state["reason"] = "deterministic_candidate_sufficient"
        return state
    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "You adjudicate DB-grounded Genshin query meaning candidates.",
                    "Return strict JSON only. Do not answer the user.",
                    "Choose only one candidate_id from the provided candidates.",
                    "Never invent candidate ids, entities, facts, source ids, or routes.",
                    "basic_lookup is allowed only for a strong supported_entity candidate.",
                    "Lore concepts, story scopes, and source-search candidates should not become basic_lookup.",
                ]
            ),
        },
        {
            "role": "user",
            "content": "\n".join(
                [
                    "/no_think",
                    "Return JSON with keys: selected_candidate_id, route, confidence, reason, uncertainty, needs_more_evidence.",
                    f"Query: {query}",
                    "Candidates:",
                    json.dumps([llm_candidate_view(item) for item in candidates[:12]], ensure_ascii=False),
                    f"Deterministic selected_candidate_id: {deterministic.get('id')}",
                ]
            ),
        },
    ]
    result = ollama_chat(messages, model=model, timeout=8.0, temperature=0.0, think=False, num_predict=384)
    state["used"] = True
    if not result.get("ok"):
        state["error"] = result.get("error")
        return state
    parsed = parse_semantic_response(str(result.get("content") or ""))
    if not parsed.get("ok"):
        state["error"] = parsed.get("error")
        state["raw_content"] = result.get("content")
        return state
    normalized = normalize_llm_adjudication(parsed["parse"])
    state.update(normalized)
    state["ok"] = True
    return state


def should_use_llm(candidates: list[dict[str, Any]], deterministic: dict[str, Any]) -> bool:
    kind = str(deterministic.get("kind") or "")
    strength = str(deterministic.get("match_strength") or "")
    if kind in {"gameplay_or_meta_unsupported", "source_or_evidence_request"}:
        return False
    if kind == "supported_entity" and strength == "strong":
        return False
    if kind == "followup_request" and deterministic.get("route_candidate") == "basic_lookup":
        return False
    if any(item.get("kind") in {"lore_concept", "region_or_story_scope", "quest_or_book_scope"} for item in candidates):
        return True
    strong = [item for item in candidates if item.get("match_strength") == "strong"]
    return len(strong) > 1


def validate_llm_selection(
    llm_state: dict[str, Any],
    candidates: list[dict[str, Any]],
    deterministic: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    if not llm_state.get("ok"):
        return deterministic, bool(llm_state.get("used"))
    by_id = {str(item.get("id")): item for item in candidates}
    candidate_id = str(llm_state.get("selected_candidate_id") or "")
    selected = by_id.get(candidate_id)
    if selected is None:
        llm_state["valid"] = False
        llm_state["error"] = {"type": "invalid_candidate_id", "message": candidate_id}
        return deterministic, True
    route = str(llm_state.get("route") or selected.get("route_candidate") or "")
    if route not in SUPPORTED_ROUTES:
        llm_state["valid"] = False
        llm_state["error"] = {"type": "invalid_route", "message": route}
        return deterministic, True
    if route == "basic_lookup" and not (
        selected.get("kind") == "supported_entity" and selected.get("match_strength") == "strong"
    ):
        llm_state["valid"] = False
        llm_state["error"] = {"type": "unsafe_basic_lookup_override", "message": candidate_id}
        return deterministic, True
    if selected.get("match_strength") == "unsafe":
        llm_state["valid"] = False
        llm_state["error"] = {"type": "unsafe_candidate_selected", "message": candidate_id}
        return deterministic, True
    llm_state["valid"] = True
    selected = dict(selected)
    selected["route_candidate"] = route
    return selected, selected.get("id") != deterministic.get("id")


def normalize_llm_adjudication(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_candidate_id": clean_text(str(data.get("selected_candidate_id") or "")) or None,
        "route": clean_text(str(data.get("route") or "")) or None,
        "confidence": clamp_float(data.get("confidence"), default=0.0),
        "reason": clean_text(str(data.get("reason") or "")),
        "uncertainty": [clean_text(str(value)) for value in data.get("uncertainty") or [] if clean_text(str(value))],
        "needs_more_evidence": bool(data.get("needs_more_evidence")),
    }


def selected_supported_resolution(query_understanding: dict[str, Any] | None) -> dict[str, Any] | None:
    selected = (query_understanding or {}).get("selected_candidate")
    if not isinstance(selected, dict):
        return None
    if selected.get("kind") != "supported_entity" or selected.get("match_strength") != "strong":
        return None
    resolution = selected.get("resolution")
    return dict(resolution) if isinstance(resolution, dict) else None


def blocks_basic_lookup(query_understanding: dict[str, Any] | None) -> bool:
    selected = (query_understanding or {}).get("selected_candidate")
    if not isinstance(selected, dict):
        return False
    kind = str(selected.get("kind") or "")
    strength = str(selected.get("match_strength") or "")
    if kind == "supported_entity" and strength == "strong":
        return False
    if kind == "followup_request" and selected.get("route_candidate") == "basic_lookup":
        return False
    if kind in {
        "gameplay_or_meta_unsupported",
        "lore_concept",
        "region_or_story_scope",
        "quest_or_book_scope",
        "source_or_evidence_request",
        "followup_request",
    } and strength == "strong":
        return True
    for item in (query_understanding or {}).get("candidates") or []:
        if item.get("kind") == "lore_concept" and item.get("match_strength") == "strong":
            supported_strong = any(
                other.get("kind") == "supported_entity" and other.get("match_strength") == "strong"
                for other in (query_understanding or {}).get("candidates") or []
            )
            if not supported_strong:
                return True
    return False


def candidate(
    candidate_id: str,
    kind: str,
    *,
    surface: str,
    route_candidate: str,
    confidence: float,
    match_strength: str,
    canonical_id: str | None = None,
    concept_id: str | None = None,
    content_type: str | None = None,
    score: Any = None,
    match_reasons: list[str] | None = None,
    risk_flags: list[str] | None = None,
    supporting_hits: list[dict[str, Any]] | None = None,
    source_refs: list[dict[str, Any]] | None = None,
    source_readable: bool | None = None,
    context_used: bool = False,
    resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    refs = source_refs if source_refs is not None else list(supporting_hits or [])
    readable = bool(source_readable) if source_readable is not None else any(ref.get("unit_id") for ref in refs)
    row = {
        "id": candidate_id,
        "candidate_id": candidate_id,
        "kind": kind,
        "candidate_type": kind,
        "surface": clean_text(surface),
        "canonical_id": canonical_id,
        "concept_id": concept_id,
        "content_type": content_type,
        "route_candidate": route_candidate,
        "confidence": clamp_float(confidence, default=0.0),
        "score": score,
        "match_strength": match_strength,
        "match_reasons": list(match_reasons or []),
        "risk_flags": list(risk_flags or []),
        "supporting_hits": refs,
        "source_refs": refs,
        "source_readable": readable,
        "context_used": context_used,
    }
    if resolution is not None:
        row["resolution"] = resolution
    return row


def supported_match_score(
    *,
    title: str,
    title_norm: str,
    query_norm: str,
    original_norm: str,
    query: str,
    content_type: str,
) -> tuple[str | None, float, list[str], list[str]]:
    reasons = []
    risks = []
    if title_norm in query_norm or title_norm in original_norm:
        reasons.append("title_exact_or_contained")
        score = 0.98 + content_type_hint_bonus(query, content_type)
        return "strong", min(score, 1.0), reasons, risks
    title_tokens = [normalize_alias(token) for token in title.split() if normalize_alias(token)]
    matched_tokens = [token for token in title_tokens if token in original_norm]
    if has_strong_partial_title_match(matched_tokens):
        reasons.append("strong_partial_title_tokens:" + ",".join(matched_tokens))
        return "strong", min(0.86 + content_type_hint_bonus(query, content_type), 1.0), reasons, risks
    if matched_tokens:
        reasons.append("weak_title_token_overlap:" + ",".join(matched_tokens))
        if len(query_norm) <= 2 or (query_norm and query_norm in title_norm and len(title_norm) > len(query_norm) + 2):
            risks.append("short_or_substring_only_title_overlap")
            return "unsafe", 0.18, reasons, risks
        return "weak", 0.38, reasons, risks
    if query_norm and query_norm in title_norm:
        reasons.append("query_inside_longer_title")
        risks.append("query_inside_much_longer_title")
        return "unsafe", 0.16, reasons, risks
    return None, 0.0, [], []


def lore_alias_match(
    alias_norm: str,
    query_norm: str,
    stripped_norm: str,
) -> tuple[str | None, float, list[str], list[str]]:
    if not query_norm and not stripped_norm:
        return None, 0.0, [], []
    haystacks = [query_norm, stripped_norm]
    if alias_norm in haystacks:
        return "strong", 0.96, ["manual_concept_alias_exact"], []
    if any(alias_norm in value for value in haystacks if value):
        return "strong", 0.9, ["manual_concept_alias_contained_in_query"], []
    if any(value and value in alias_norm for value in haystacks):
        if max(len(query_norm), len(stripped_norm)) <= 2:
            return "weak", 0.46, ["query_inside_longer_concept_alias"], ["short_query_inside_concept_alias"]
        return "weak", 0.58, ["query_inside_longer_concept_alias"], []
    return None, 0.0, [], []


def load_lore_concepts(root: Path) -> list[dict[str, Any]]:
    path = root / "config" / "search_engine_manual_concepts.json"
    if not path.exists():
        return []
    rows = read_json(path)
    return [row for row in rows if isinstance(row, dict) and row.get("concept_id")]


def concept_aliases(concept: dict[str, Any]) -> list[dict[str, str]]:
    rows = []
    primary = clean_text(str(concept.get("primary_name") or ""))
    if primary:
        rows.append({"language": "ko", "name": primary})
    for language, aliases in (concept.get("aliases") or {}).items():
        for alias in aliases or []:
            alias_text = clean_text(str(alias or ""))
            if alias_text:
                rows.append({"language": str(language), "name": alias_text})
    deduped = {}
    for row in rows:
        deduped[(row["language"], normalize_alias(row["name"]))] = row
    return list(deduped.values())


def concept_supporting_hits(db_path: Path, alias: str, *, language: str) -> list[dict[str, Any]]:
    return [source_ref_from_hit(hit) for hit in safe_search(db_path, alias, language=language, limit=3, include_textmap=False)]


def safe_search(
    db_path: Path,
    query: str,
    *,
    language: str | None,
    limit: int,
    include_textmap: bool,
) -> list[dict[str, Any]]:
    if not db_path.exists() or not clean_text(query):
        return []
    try:
        return search_project_amber_v2(
            db_path,
            query,
            language=language,
            limit=limit,
            mode="unicode",
            include_textmap=include_textmap,
        )
    except Exception:
        return []


def supported_title_rows(db_path: Path, *, language: str) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
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


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in candidates:
        candidate_id = str(item.get("id") or "")
        if not candidate_id:
            continue
        existing = by_id.get(candidate_id)
        if existing is None or candidate_sort_key(item, query=str(item.get("surface") or "")) > candidate_sort_key(
            existing, query=str(existing.get("surface") or "")
        ):
            by_id[candidate_id] = item
        elif existing is not None:
            existing["match_reasons"] = sorted(set(existing.get("match_reasons") or []) | set(item.get("match_reasons") or []))
            existing["risk_flags"] = sorted(set(existing.get("risk_flags") or []) | set(item.get("risk_flags") or []))
            existing["source_refs"] = [*(existing.get("source_refs") or []), *(item.get("source_refs") or [])]
            existing["supporting_hits"] = existing["source_refs"]
            existing["source_readable"] = bool(existing.get("source_readable") or item.get("source_readable"))
    return list(by_id.values())


def mark_supported_conflicts(candidates: list[dict[str, Any]]) -> None:
    strong_lore = any(item.get("kind") == "lore_concept" and item.get("match_strength") == "strong" for item in candidates)
    if not strong_lore:
        return
    for item in candidates:
        if item.get("kind") == "supported_entity" and item.get("match_strength") != "strong":
            flags = set(item.get("risk_flags") or [])
            flags.add("supported_entity_conflicts_with_strong_lore_concept")
            item["risk_flags"] = sorted(flags)


def unknown_candidate(query: str) -> dict[str, Any]:
    return candidate(
        "unknown:low_information",
        "unknown_or_low_information",
        surface=query,
        route_candidate="analysis",
        confidence=0.2,
        match_strength="weak",
        match_reasons=["no_db_grounded_candidate_found"],
        risk_flags=["low_information_or_no_match"],
    )


def conversation_context_summary(
    query: str,
    state: ConversationState | None,
    conversation_context: dict[str, Any] | None,
) -> dict[str, Any]:
    active = state.active_entity if state else None
    actual_used = bool((conversation_context or {}).get("context_used"))
    explicit_topic = has_explicit_topic_signal(query)
    return {
        "available": bool(active or (state and state.last_sources)),
        "active_entity": active,
        "last_route": state.last_route if state else None,
        "last_intent": state.last_intent if state else None,
        "last_sources_count": len(state.last_sources) if state else 0,
        "used": actual_used,
        "reference": (conversation_context or {}).get("context_reference"),
        "resolved_query": (conversation_context or {}).get("resolved_query"),
        "explicit_topic_detected": explicit_topic,
        "rejected_reason": "explicit_topic" if explicit_topic and not actual_used else None,
    }


def has_explicit_topic_signal(query: str) -> bool:
    remainder = normalize_alias(strip_query_hints(query))
    for term in [*INTENT_ONLY_TERMS, *DETAIL_TERMS, *SUMMARY_TERMS, *STORY_SCOPE_TERMS, *FOLLOWUP_FILLER_TERMS]:
        normalized = normalize_alias(term)
        if normalized:
            remainder = remainder.replace(normalized, "")
    return len(remainder) >= 2


def is_low_information_followup(query: str) -> bool:
    normalized = normalize_alias(query)
    if normalized in LOW_INFORMATION_REMAINDERS:
        return True
    for term in [*INTENT_ONLY_TERMS, *DETAIL_TERMS, *SUMMARY_TERMS, *STORY_SCOPE_TERMS, *FOLLOWUP_FILLER_TERMS]:
        normalized = normalized.replace(normalize_alias(term), "")
    return normalized in LOW_INFORMATION_REMAINDERS or len(normalized) <= 1


def is_context_only_source_followup(query: str) -> bool:
    normalized = normalize_alias(query)
    if not any(normalize_alias(term) in normalized for term in SOURCE_READER_TERMS):
        return False
    remainder = normalized
    for term in [*SOURCE_READER_TERMS, *FOLLOWUP_FILLER_TERMS]:
        normalized_term = normalize_alias(term)
        if normalized_term:
            remainder = remainder.replace(normalized_term, "")
    return remainder in LOW_INFORMATION_REMAINDERS or len(remainder) <= 1


def looks_like_story_scope(query: str) -> bool:
    normalized = normalize_alias(query)
    return any(normalize_alias(term) in normalized for term in STORY_SCOPE_TERMS)


def has_strong_partial_title_match(matched_tokens: list[str]) -> bool:
    meaningful_tokens = [token for token in matched_tokens if len(token) >= 2]
    if len(meaningful_tokens) >= 2:
        return True
    if meaningful_tokens and len(meaningful_tokens[0]) >= 3:
        return True
    return len(matched_tokens) >= 2 and sum(len(token) for token in matched_tokens) >= 3


def strip_query_hints(query: str) -> str:
    stripped = str(query)
    for hint in sorted(QUERY_HINTS, key=len, reverse=True):
        stripped = stripped.replace(hint, " ")
    return clean_text(stripped)


def content_type_hint_bonus(query: str, content_type: str) -> float:
    normalized = normalize_alias(query)
    if content_type == "reliquary" and ("성유물" in normalized or "효과" in normalized):
        return 0.02
    if content_type == "weapon" and ("무기" in normalized or "효과" in normalized or "제련" in normalized or "재련" in normalized):
        return 0.02
    if content_type == "avatar" and ("캐릭터" in normalized or "기본정보" in normalized):
        return 0.02
    return 0.0


def source_ref_from_resolution(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "canonical_id": row.get("canonical_id"),
        "content_type": row.get("content_type"),
        "title": row.get("title"),
        "language": row.get("language"),
        "source_url": row.get("source_url"),
        "raw_ref": row.get("raw_ref"),
    }


def source_ref_from_hit(hit: dict[str, Any]) -> dict[str, Any]:
    return {
        "result_type": hit.get("result_type"),
        "unit_id": hit.get("unit_id"),
        "chunk_id": hit.get("chunk_id"),
        "document_id": hit.get("document_id"),
        "section_id": hit.get("section_id"),
        "canonical_id": hit.get("canonical_id"),
        "content_type": hit.get("content_type"),
        "title": hit.get("title"),
        "language": hit.get("language"),
        "source_url": hit.get("source_url"),
        "textmap_id": (hit.get("textmap_id") or hit.get("id")) if hit.get("result_type") == "textmap" else None,
    }


def source_refs_from_state(state: ConversationState | None) -> list[dict[str, Any]]:
    if state is None:
        return []
    return [dict(source) for source in state.last_sources if is_source_context(source)]


def llm_candidate_view(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "kind": item.get("kind"),
        "surface": item.get("surface"),
        "canonical_id": item.get("canonical_id"),
        "concept_id": item.get("concept_id"),
        "content_type": item.get("content_type"),
        "route_candidate": item.get("route_candidate"),
        "match_strength": item.get("match_strength"),
        "confidence": item.get("confidence"),
        "match_reasons": item.get("match_reasons"),
        "risk_flags": item.get("risk_flags"),
        "source_readable": item.get("source_readable"),
    }


def clamp_float(value: Any, *, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default
