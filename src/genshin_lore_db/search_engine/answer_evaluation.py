from __future__ import annotations

import re
from pathlib import Path
from statistics import mean
from typing import Any

from genshin_lore_db.io import read_json, utc_now
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.search_engine.conversation import ConversationState
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL
from genshin_lore_db.search_engine.qa import answer_question


METRIC_NAMES = [
    "intent_match",
    "route_match",
    "content_type_match",
    "canonical_id_match",
    "item_id_match",
    "required_fragments_present",
    "forbidden_fragments_absent",
    "requested_style_match",
    "unsupported_reason_match",
    "context_used_match",
    "plan_intent_match",
    "validation_ok",
    "case_passed",
]


def evaluate_answer_engine(
    root: Path | str,
    evaluation_set: dict[str, Any],
    *,
    use_llm: bool = False,
    model: str = DEFAULT_OLLAMA_MODEL,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    cases = [
        evaluate_answer_case(root_path, case, use_llm=use_llm, model=model)
        for case in evaluation_set.get("cases") or []
    ]
    aggregate = aggregate_metrics(cases)
    thresholds = evaluation_set.get("thresholds") or {}
    return {
        "version": str(evaluation_set.get("version") or "0.6.0"),
        "evaluated_at": utc_now(),
        "mode": "llm" if use_llm else "no_llm",
        "model": model if use_llm else None,
        "case_count": len(cases),
        "thresholds": thresholds,
        "aggregate": aggregate,
        "passed_thresholds": threshold_results(aggregate, thresholds),
        "cases": cases,
    }


def evaluate_answer_case(
    root: Path,
    case: dict[str, Any],
    *,
    use_llm: bool,
    model: str,
) -> dict[str, Any]:
    query = str(case["query"])
    conversation_state = conversation_state_from_history(root, case.get("history") or [], use_llm=use_llm, model=model)
    result = answer_question(root, query, use_llm=use_llm, model=model, conversation_state=conversation_state)
    route = result.get("route") or {}
    plan = route.get("answer_plan") if isinstance(route.get("answer_plan"), dict) else {}
    final_answer = str(result.get("final_answer") or "")

    required_fragments = [str(value) for value in case.get("required_fragments") or []]
    forbidden_fragments = [str(value) for value in case.get("forbidden_fragments") or []]
    missing_required = [
        fragment
        for fragment in required_fragments
        if compact_for_match(fragment) not in compact_for_match(final_answer)
    ]
    present_forbidden = [
        fragment
        for fragment in forbidden_fragments
        if compact_for_match(fragment) in compact_for_match(final_answer)
    ]

    checks = {
        "intent_match": expected_matches(case, "expected_intent", result.get("intent")),
        "route_match": expected_matches(case, "expected_route", route.get("mode")),
        "content_type_match": expected_matches(case, "expected_content_type", result.get("content_type")),
        "canonical_id_match": expected_matches(case, "expected_canonical_id", result.get("canonical_id")),
        "item_id_match": expected_matches(case, "expected_item_id", result.get("item_id")),
        "required_fragments_present": not missing_required,
        "forbidden_fragments_absent": not present_forbidden,
        "requested_style_match": expected_matches(
            case,
            "expected_requested_style",
            result.get("requested_style") or route.get("requested_style"),
        ),
        "unsupported_reason_match": expected_matches(case, "expected_unsupported_reason", route.get("unsupported_reason")),
        "context_used_match": expected_bool_matches(case, "expected_context_used", route.get("context_used")),
        "plan_intent_match": expected_matches(
            case,
            "expected_plan_intent",
            plan.get("intent") or route.get("intent"),
        ),
        "validation_ok": bool((result.get("validation") or {}).get("ok")),
    }
    checks["case_passed"] = all(checks.values())

    return {
        "id": case.get("id"),
        "query": query,
        "route": route,
        "expected": {
            "intent": case.get("expected_intent"),
            "route": case.get("expected_route"),
            "content_type": case.get("expected_content_type"),
            "canonical_id": case.get("expected_canonical_id"),
            "item_id": case.get("expected_item_id"),
            "requested_style": case.get("expected_requested_style"),
            "unsupported_reason": case.get("expected_unsupported_reason"),
            "context_used": case.get("expected_context_used"),
            "plan_intent": case.get("expected_plan_intent"),
        },
        "actual": {
            "intent": result.get("intent"),
            "content_type": result.get("content_type"),
            "canonical_id": result.get("canonical_id"),
            "item_id": result.get("item_id"),
            "requested_style": result.get("requested_style") or route.get("requested_style"),
            "unsupported_reason": route.get("unsupported_reason"),
            "context_used": route.get("context_used"),
            "plan_intent": plan.get("intent") or route.get("intent"),
            "validation": result.get("validation"),
            "llm": result.get("llm"),
        },
        "missing_required_fragments": missing_required,
        "present_forbidden_fragments": present_forbidden,
        "metrics": {name: 1.0 if checks[name] else 0.0 for name in METRIC_NAMES},
        "passed": checks["case_passed"],
        "final_answer": final_answer,
    }


def conversation_state_from_history(
    root: Path,
    history: list[Any],
    *,
    use_llm: bool,
    model: str,
) -> ConversationState:
    state = ConversationState()
    for turn in history:
        if isinstance(turn, str):
            historical_result = answer_question(root, turn, use_llm=use_llm, model=model, conversation_state=state)
            state.update_from_result(historical_result)
            continue
        if not isinstance(turn, dict):
            continue
        if isinstance(turn.get("state"), dict):
            apply_state_patch(state, turn["state"])
        if isinstance(turn.get("active_entity"), dict):
            state.active_entity = dict(turn["active_entity"])
        query = turn.get("user") or turn.get("query")
        if query:
            historical_result = answer_question(root, str(query), use_llm=use_llm, model=model, conversation_state=state)
            state.update_from_result(historical_result)
    return state


def apply_state_patch(state: ConversationState, patch: dict[str, Any]) -> None:
    for key in [
        "active_entity",
        "active_topic",
        "last_route",
        "last_intent",
        "last_answer_style",
        "last_sources",
        "turn_count",
    ]:
        if key in patch:
            setattr(state, key, patch[key])


def aggregate_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    aggregate = {}
    for name in METRIC_NAMES:
        values = [float(case["metrics"][name]) for case in cases]
        aggregate[name] = round(mean(values), 4) if values else 0.0
    return aggregate


def threshold_results(aggregate: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, bool]:
    return {
        metric: float(aggregate.get(metric, 0.0)) >= float(threshold)
        for metric, threshold in thresholds.items()
    }


def expected_matches(case: dict[str, Any], key: str, actual: Any) -> bool:
    if key not in case:
        return True
    expected = case.get(key)
    if expected is None:
        return actual is None
    return str(expected) == str(actual)


def expected_bool_matches(case: dict[str, Any], key: str, actual: Any) -> bool:
    if key not in case:
        return True
    expected = case.get(key)
    if expected is None:
        return actual is None
    return bool(expected) is bool(actual)


def compact_for_match(value: str) -> str:
    return re.sub(r"\s+", "", clean_text(value))


def load_answer_evaluation_set(path: Path | str) -> dict[str, Any]:
    return read_json(Path(path))
