from __future__ import annotations

import json
import socket
import urllib.error
import urllib.request
from typing import Any


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2:1b"


def rewrite_answer_with_ollama(
    *,
    facts: dict[str, Any],
    draft_answer: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 20.0,
    temperature: float = 0.2,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "너는 원신 공식 데이터 답변을 다듬는 한국어 rewriter다.",
                    "FACTS와 DRAFT에 있는 정보만 사용한다.",
                    "새로운 사실, 숫자, 이름, 추천, 추측을 추가하지 않는다.",
                    "숫자와 고유명사는 절대 바꾸지 않는다.",
                    "JSON, 코드블록, 설명문, 검증문을 출력하지 않는다.",
                    "최종 답변 본문만 짧은 문단과 불릿으로 출력한다.",
                ]
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    "허용된 핵심 정보:",
                    compact_facts_for_prompt(facts),
                    "DRAFT:",
                    draft_answer,
                    "위 DRAFT의 의미를 바꾸지 말고 어색한 표현만 다듬어라. 최종 답변만 출력하라.",
                ]
            ),
        },
    ]
    return ollama_chat(
        messages,
        model=model,
        base_url=base_url,
        timeout=timeout,
        temperature=temperature,
    )


def compact_facts_for_prompt(facts: dict[str, Any]) -> str:
    lines = []
    for key in ["intent", "name", "rank", "content_type", "weapon_type", "element", "region", "birthday"]:
        if facts.get(key) is not None:
            lines.append(f"- {key}: {facts[key]}")
    for effect in facts.get("effects") or []:
        label = f"{effect.get('pieces')}세트" if effect.get("pieces") else effect.get("id")
        lines.append(f"- {label}: {effect.get('text')}")
    for affix in facts.get("affixes") or []:
        if affix.get("name"):
            lines.append(f"- 무기 효과 이름: {affix['name']}")
        refinements = affix.get("refinements") or []
        if refinements:
            lines.append(f"- 1재련 효과: {refinements[0].get('text')}")
    for key in ["title", "detail", "constellation", "special_prop"]:
        if facts.get(key):
            lines.append(f"- {key}: {facts[key]}")
    return "\n".join(lines[:24])


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 20.0,
    temperature: float = 0.2,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": temperature,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return error_result(
            model=model,
            error_type="http_error",
            message=http_error_message(exc),
            status=exc.code,
        )
    except urllib.error.URLError as exc:
        return error_result(
            model=model,
            error_type="connection_error",
            message=str(exc.reason),
        )
    except (TimeoutError, socket.timeout) as exc:
        return error_result(
            model=model,
            error_type="timeout",
            message=str(exc),
        )
    except OSError as exc:
        return error_result(
            model=model,
            error_type="os_error",
            message=str(exc),
        )

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        return error_result(
            model=model,
            error_type="invalid_json",
            message=str(exc),
        )
    content = str((data.get("message") or {}).get("content") or "").strip()
    if not content:
        return error_result(
            model=model,
            error_type="empty_response",
            message="Ollama returned an empty message.",
            raw=data,
        )
    return {
        "ok": True,
        "provider": "ollama",
        "model": model,
        "content": content,
        "error": None,
    }


def http_error_message(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        body = ""
    return body.strip() or str(exc)


def error_result(
    *,
    model: str,
    error_type: str,
    message: str,
    status: int | None = None,
    raw: Any = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {
        "type": error_type,
        "message": message,
    }
    if status is not None:
        error["status"] = status
    return {
        "ok": False,
        "provider": "ollama",
        "model": model,
        "content": "",
        "error": error,
        "raw": raw,
    }
