from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConversationState:
    active_entity: dict[str, Any] | None = None
    active_topic: str | None = None
    last_route: str | None = None
    last_intent: str | None = None
    last_answer_style: str | None = None
    last_sources: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_entity": self.active_entity,
            "active_topic": self.active_topic,
            "last_route": self.last_route,
            "last_intent": self.last_intent,
            "last_answer_style": self.last_answer_style,
            "last_sources": list(self.last_sources),
            "turn_count": self.turn_count,
        }

    def update_from_result(self, result: dict[str, Any]) -> None:
        self.turn_count += 1
        route = result.get("route") if isinstance(result.get("route"), dict) else {}
        intent = str(result.get("intent") or route.get("intent") or "")
        self.last_route = str(route.get("mode") or "") or self.last_route
        self.last_intent = intent or self.last_intent
        self.last_answer_style = str(result.get("requested_style") or route.get("requested_style") or "") or self.last_answer_style
        self.last_sources = list(result.get("sources") or [])

        canonical_id = result.get("canonical_id")
        content_type = result.get("content_type")
        facts = result.get("facts") if isinstance(result.get("facts"), dict) else {}
        name = facts.get("name")
        if canonical_id and content_type and name:
            self.active_entity = {
                "name": name,
                "content_type": content_type,
                "canonical_id": canonical_id,
                "item_id": result.get("item_id"),
            }
            self.active_topic = topic_for_intent(intent)


def topic_for_intent(intent: str | None) -> str | None:
    if intent == "character_basic_info":
        return "profile"
    if intent == "weapon_basic_info":
        return "weapon_basic_info"
    if intent == "reliquary_effect_lookup":
        return "reliquary_effect"
    if intent == "character_constellation":
        return "character_constellation"
    if intent == "character_talent":
        return "character_talent"
    return intent
