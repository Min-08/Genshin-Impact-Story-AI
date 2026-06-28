from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from genshin_lore_db.normalize import clean_text


ANSWER_PLAN_VERSION = "answer_plan.v0.1"

ANSWER_PLAN_ROUTES = {
    "basic_lookup",
    "summary",
    "analysis",
    "research",
    "source_reader",
    "chitchat",
    "unsupported",
}
REQUESTED_STYLES = {"brief", "default", "detail", "raw", "evidence", "analysis", "research"}
DETAIL_LEVELS = {"low", "medium", "high"}


@dataclass
class AnswerPlan:
    route: str
    intent: str | None = None
    entities: list[dict[str, Any]] = field(default_factory=list)
    requested_style: str = "default"
    detail_level: str = "medium"
    context_reference: str | None = None
    context_used: bool = False
    needs_evidence: bool = False
    needs_raw_source: bool = False
    needs_clarification: bool = False
    unsupported_reason: str | None = None
    confidence: float = 0.0
    parser: str = "deterministic"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["schema_version"] = ANSWER_PLAN_VERSION
        return data


def normalize_answer_plan(data: dict[str, Any] | None, *, parser: str = "llm") -> AnswerPlan | None:
    if not isinstance(data, dict):
        return None
    route = normalize_choice(data.get("route"), ANSWER_PLAN_ROUTES, default="unsupported")
    requested_style = normalize_choice(data.get("requested_style"), REQUESTED_STYLES, default="default")
    detail_level = normalize_choice(data.get("detail_level"), DETAIL_LEVELS, default="medium")
    entities = []
    for row in data.get("entities") or []:
        if not isinstance(row, dict):
            continue
        name = clean_text(str(row.get("name") or row.get("surface") or ""))
        if not name:
            continue
        entities.append(
            {
                "surface": name,
                "name": name,
                "type": clean_text(str(row.get("type") or row.get("content_type_hint") or "")) or None,
                "confidence": clamp_float(row.get("confidence"), default=0.0),
            }
        )
    return AnswerPlan(
        route=route,
        intent=clean_text(str(data.get("intent") or "")) or None,
        entities=entities,
        requested_style=requested_style,
        detail_level=detail_level,
        context_reference=clean_text(str(data.get("context_reference") or "")) or None,
        context_used=bool(data.get("context_used")),
        needs_evidence=bool(data.get("needs_evidence")),
        needs_raw_source=bool(data.get("needs_raw_source")),
        needs_clarification=bool(data.get("needs_clarification")),
        unsupported_reason=clean_text(str(data.get("unsupported_reason") or "")) or None,
        confidence=clamp_float(data.get("confidence"), default=0.0),
        parser=parser,
    )


def normalize_choice(value: Any, allowed: set[str], *, default: str) -> str:
    text = clean_text(str(value or ""))
    return text if text in allowed else default


def clamp_float(value: Any, *, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default
