from __future__ import annotations

import re
from typing import Any, Iterable

from .io import sha256_text


TITLE_FIELDS = ["name", "title", "chapterTitle"]
TEXT_FIELD_HINTS = {
    "name",
    "title",
    "chapterTitle",
    "chapterNum",
    "chapterImageTitle",
    "description",
    "detail",
    "text",
    "role",
    "native",
    "constellation",
}
SKIP_FIELD_HINTS = {
    "icon",
    "route",
    "source_url",
    "content_hash",
    "raw_id",
    "fetched_at",
    "crawler_version",
    "raw_format",
    "metadata",
    "params",
    "costItems",
    "addProps",
    "advancedProps",
    "upgrade",
    "ascension",
}


def extract_text(payload: Any, *, content_type: str | None) -> str:
    lines: list[str] = []
    if content_type == "quest":
        lines.extend(_extract_quest_lines(payload))
    lines.extend(_extract_generic_lines(payload))
    deduped = _dedupe_keep_order(clean_text(line) for line in lines)
    return "\n".join(line for line in deduped if line)


def _extract_quest_lines(payload: Any) -> list[str]:
    lines: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            role = value.get("role")
            text = value.get("text")
            if isinstance(role, str) and isinstance(text, str):
                lines.append(f"{role}: {text}")
            if isinstance(role, str) and isinstance(text, list):
                for choice in text:
                    if isinstance(choice, dict) and isinstance(choice.get("text"), str):
                        lines.append(f"{role}: {choice['text']}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return lines


def _extract_generic_lines(payload: Any, parent_key: str | None = None) -> list[str]:
    lines: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            if key_text in SKIP_FIELD_HINTS:
                continue
            if isinstance(value, str):
                if _should_keep_string(key_text, value):
                    label = _friendly_label(key_text)
                    lines.append(f"{label}: {value}" if label else value)
            else:
                lines.extend(_extract_generic_lines(value, key_text))
    elif isinstance(payload, list):
        for value in payload:
            lines.extend(_extract_generic_lines(value, parent_key))
    return lines


def _should_keep_string(key: str, value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    if key in TEXT_FIELD_HINTS:
        return True
    if any(hint in key.lower() for hint in ["name", "title", "desc", "story", "text", "role"]):
        return True
    if re.search(r"[\u3131-\uD79D\u3040-\u30FF\u3400-\u9FFF]", stripped):
        return True
    if len(stripped.split()) >= 4:
        return True
    return False


def _friendly_label(key: str) -> str | None:
    if key in {"text", "description", "detail"}:
        return None
    return key


def clean_text(value: str) -> str:
    value = str(value)
    value = re.sub(r"<color=#[0-9A-Fa-f]+>", "", value)
    value = value.replace("</color>", "")
    value = value.replace("<i>", "").replace("</i>", "")
    value = value.replace("\\n", "\n")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        fingerprint = sha256_text(normalized)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(normalized)
    return result
