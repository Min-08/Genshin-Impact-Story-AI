from __future__ import annotations

import json
import re
from typing import Any

from genshin_lore_db.normalize import clean_text
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, ollama_chat


SEMANTIC_SCHEMA_VERSION = "semantic_parse.v0.1"
SEMANTIC_ROUTES = {"basic_lookup", "summary", "analysis", "research", "chitchat", "unsupported"}
SEMANTIC_FORMATS = {"paragraph", "bullet", "table", "short", "long"}


def parse_query_semantics_with_ollama(
    query: str,
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    timeout: float = 8.0,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "You classify a Korean Genshin Impact lore/game-data query.",
                    "Return strict JSON only. Do not write markdown, prose, or reasoning.",
                    "Do not invent entities. Use the user's surface strings only.",
                    "Allowed route values: basic_lookup, summary, analysis, research, chitchat, unsupported.",
                    "Allowed requested_format values: paragraph, bullet, table, short, long.",
                    "너는 질문 의미를 JSON으로만 분류한다. 답변을 생성하지 않는다.",
                    "엔티티는 사용자가 말한 표면 문자열만 넣고 새 이름을 만들지 않는다.",
                ]
            ),
        },
        {
            "role": "user",
            "content": "\n".join(
                [
                    "/no_think",
                    "다음 JSON 스키마로만 답하라:",
                    '{"schema_version":"semantic_parse.v0.1","route":"basic_lookup","intent":"character_basic_info","entities":[{"surface":"아야카","content_type_hint":"avatar","confidence":0.8}],"requested_format":"paragraph","depth":0,"is_greeting":false,"is_followup":false,"needs_official_sources":true,"risk_flags":[],"confidence":0.8,"reason":"..."}',
                    f"질문: {query}",
                ]
            ),
        },
    ]
    result = ollama_chat(
        messages,
        model=model,
        timeout=timeout,
        temperature=0.0,
        think=False,
        num_predict=256,
    )
    if not result.get("ok"):
        return {
            "ok": False,
            "provider": result.get("provider") or "ollama",
            "model": model,
            "parse": None,
            "error": result.get("error"),
        }
    parsed = parse_semantic_response(str(result.get("content") or ""))
    if not parsed.get("ok"):
        return {
            "ok": False,
            "provider": result.get("provider") or "ollama",
            "model": model,
            "parse": None,
            "error": parsed.get("error"),
            "raw_content": result.get("content"),
        }
    return {
        "ok": True,
        "provider": result.get("provider") or "ollama",
        "model": model,
        "parse": normalize_semantic_parse(parsed["parse"]),
        "error": None,
    }


def parse_semantic_response(content: str) -> dict[str, Any]:
    raw = clean_text(content)
    raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    raw = re.sub(r"\s*```$", "", raw)
    candidate = extract_json_object(raw)
    if not candidate:
        return {"ok": False, "error": {"type": "semantic_parse_invalid_json", "message": "No JSON object found."}}
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": {"type": "semantic_parse_invalid_json", "message": str(exc)}}
    if not isinstance(data, dict):
        return {"ok": False, "error": {"type": "semantic_parse_invalid_shape", "message": "Root must be an object."}}
    return {"ok": True, "parse": data}


def extract_json_object(content: str) -> str | None:
    start = content.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escape = False
    for index, char in enumerate(content[start:], start=start):
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1]
    return None


def normalize_semantic_parse(data: dict[str, Any]) -> dict[str, Any]:
    route = str(data.get("route") or "unsupported").strip()
    if route not in SEMANTIC_ROUTES:
        route = "unsupported"
    requested_format = str(data.get("requested_format") or "paragraph").strip()
    if requested_format not in SEMANTIC_FORMATS:
        requested_format = "paragraph"
    entities = []
    for row in data.get("entities") or []:
        if not isinstance(row, dict):
            continue
        surface = clean_text(str(row.get("surface") or ""))
        if not surface:
            continue
        entities.append(
            {
                "surface": surface,
                "content_type_hint": clean_text(str(row.get("content_type_hint") or "")) or None,
                "confidence": clamp_float(row.get("confidence"), default=0.0),
            }
        )
    return {
        "schema_version": SEMANTIC_SCHEMA_VERSION,
        "route": route,
        "intent": clean_text(str(data.get("intent") or "")) or None,
        "entities": entities,
        "requested_format": requested_format,
        "depth": clamp_int(data.get("depth"), default=0, minimum=0, maximum=3),
        "is_greeting": bool(data.get("is_greeting")),
        "is_followup": bool(data.get("is_followup")),
        "needs_official_sources": bool(data.get("needs_official_sources", True)),
        "risk_flags": [clean_text(str(value)) for value in data.get("risk_flags") or [] if clean_text(str(value))],
        "confidence": clamp_float(data.get("confidence"), default=0.0),
        "reason": clean_text(str(data.get("reason") or "")),
    }


def clamp_float(value: Any, *, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def clamp_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))
