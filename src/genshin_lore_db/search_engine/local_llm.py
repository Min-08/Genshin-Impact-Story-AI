from __future__ import annotations

import json
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "qwen3:4b-instruct"


def ensure_local_llm_ready(
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    auto_start: bool = True,
    startup_timeout: float = 8.0,
    request_timeout: float = 2.0,
) -> dict[str, Any]:
    status = {
        "available": False,
        "status": "server_unavailable",
        "server_reachable": False,
        "model_available": False,
        "auto_start_attempted": False,
        "auto_started": False,
        "ollama_path": None,
        "model": model,
        "base_url": base_url,
        "message": "",
        "pull_command": f"ollama pull {model}",
    }
    if ollama_api_reachable(base_url=base_url, timeout=request_timeout):
        status["server_reachable"] = True
    elif auto_start:
        ollama_path = find_ollama_executable()
        status["ollama_path"] = ollama_path
        if not ollama_path:
            status.update(
                {
                    "status": "ollama_missing",
                    "message": "Ollama is not installed or is not on PATH. Install Ollama, then run the terminal again.",
                }
            )
            return status
        status["auto_start_attempted"] = True
        if start_ollama_server(ollama_path):
            status["auto_started"] = True
            status["server_reachable"] = wait_for_ollama(
                base_url=base_url,
                timeout=startup_timeout,
                request_timeout=request_timeout,
            )
    else:
        status["ollama_path"] = find_ollama_executable()

    if not status["server_reachable"]:
        status.update(
            {
                "status": "server_unavailable",
                "message": "Ollama API is not reachable. Continuing without local LLM.",
            }
        )
        return status

    if not ollama_model_available(model, base_url=base_url, timeout=request_timeout):
        status.update(
            {
                "status": "model_missing",
                "model_available": False,
                "message": f"Ollama is running, but model '{model}' is missing. Run: ollama pull {model}",
            }
        )
        return status

    status.update(
        {
            "available": True,
            "status": "available",
            "model_available": True,
            "message": "Ollama local LLM is available.",
        }
    )
    return status


def find_ollama_executable() -> str | None:
    found = shutil.which("ollama")
    if found:
        return found
    candidates = [
        Path.home() / "AppData" / "Local" / "Programs" / "Ollama" / "ollama.exe",
        Path("C:/Program Files/Ollama/ollama.exe"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


def ensure_ollama_server(
    ollama_path: str,
    *,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 60.0,
    request_timeout: float = 5.0,
) -> dict[str, Any]:
    if ollama_api_reachable(base_url=base_url, timeout=request_timeout):
        return {"step": "ensure_server", "ok": True, "status": "already_running"}
    if not start_ollama_server(ollama_path):
        return {"step": "ensure_server", "ok": False, "error": "Failed to start Ollama server."}
    if wait_for_ollama(base_url=base_url, timeout=min(timeout, 60.0), request_timeout=request_timeout):
        return {"step": "ensure_server", "ok": True, "status": "started"}
    return {"step": "ensure_server", "ok": False, "error": "Ollama server did not become ready."}


def ollama_api_reachable(*, base_url: str = DEFAULT_OLLAMA_URL, timeout: float = 2.0) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/version", timeout=timeout) as response:
            return response.status == 200
    except (OSError, urllib.error.URLError):
        return False


def wait_for_ollama(
    *,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 8.0,
    request_timeout: float = 2.0,
    interval: float = 0.5,
) -> bool:
    deadline = time.time() + max(0.0, timeout)
    while time.time() < deadline:
        if ollama_api_reachable(base_url=base_url, timeout=request_timeout):
            return True
        time.sleep(interval)
    return ollama_api_reachable(base_url=base_url, timeout=request_timeout)


def start_ollama_server(ollama_path: str) -> bool:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        subprocess.Popen(
            [ollama_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except OSError:
        return False
    return True


def ollama_model_available(
    model: str,
    *,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 2.0,
) -> bool:
    try:
        with urllib.request.urlopen(base_url.rstrip("/") + "/api/tags", timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return False
    for row in data.get("models") or []:
        if not isinstance(row, dict):
            continue
        if model in {str(row.get("name") or ""), str(row.get("model") or "")}:
            return True
    return False


def rewrite_answer_with_ollama(
    *,
    facts: dict[str, Any],
    draft_answer: str,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 60.0,
    temperature: float = 0.2,
    think: bool = False,
    num_predict: int = 96,
) -> dict[str, Any]:
    messages = [
        {
            "role": "system",
            "content": "\n".join(
                [
                    "You write one short Korean lead sentence for verified game facts.",
                    "Do not output reasoning, analysis, explanations, or <think> blocks.",
                    "Output exactly one sentence, no bullets.",
                    "Do not include numbers, percentages, quoted names, CV names, effect values, or source text.",
                    "Do not summarize or paraphrase the facts.",
                    "너는 검증된 원신 공식 데이터 답변 앞에 붙일 짧은 한국어 리드 문장만 쓴다.",
                    "한 문장만 출력한다. 불릿, JSON, 코드블록, 설명문은 금지한다.",
                    "숫자, 퍼센트, 따옴표 안의 이름, CV 이름, 효과 수치, 출처 문구는 쓰지 않는다.",
                    "사실을 요약하거나 바꿔 말하지 말고, 답변을 자연스럽게 시작하는 문장만 쓴다.",
                ]
            ),
        },
        {
            "role": "user",
            "content": "\n\n".join(
                [
                    "/no_think",
                    "허용된 핵심 정보:",
                    "/no_think",
                    compact_facts_for_prompt(facts),
                    "DRAFT:",
                    draft_answer,
                    "DRAFT 앞에 붙일 짧은 리드 문장 하나만 출력하라.",
                ]
            ),
        },
    ]
    result = ollama_chat(
        messages,
        model=model,
        base_url=base_url,
        timeout=timeout,
        temperature=temperature,
        think=think,
        num_predict=num_predict,
    )
    if result.get("ok"):
        lead = safe_lead_sentence(str(result.get("content") or ""), facts)
        result["content"] = f"{lead}\n{draft_answer}"
        result["rewrite_mode"] = "lead_sentence_plus_verified_draft"
    return result


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


def safe_lead_sentence(candidate: str, facts: dict[str, Any]) -> str:
    fallback = default_lead_sentence(facts)
    line = ""
    for raw_line in candidate.splitlines():
        stripped = raw_line.strip(" \t-*•")
        if stripped:
            line = stripped
            break
    if not line:
        return fallback
    line = re.split(r"(?<=[.!?。！？])\s+", line, maxsplit=1)[0].strip()
    line = line.strip('"').strip("'").strip()
    if not line:
        return fallback
    if len(line) > 72:
        return fallback
    if re.search(r"\d|%|「|」|\"|'", line):
        return fallback
    primary_name = str(facts.get("name") or "").strip()
    if primary_name and primary_name in line:
        return fallback
    fact_tokens = lead_rejection_tokens(facts)
    compact_line = re.sub(r"\s+", "", line)
    if any(token in compact_line for token in fact_tokens):
        return fallback
    forbidden_terms = ["추천", "티어", "추측", "가능성", "강력", "최고", "필수"]
    if any(term in line for term in forbidden_terms):
        return fallback
    if line[-1] not in ".!?。！？":
        line += "."
    return line


def lead_rejection_tokens(facts: dict[str, Any]) -> set[str]:
    values: list[str] = []
    for key in ["element", "weapon_type", "region", "birthday", "constellation", "special_prop", "title"]:
        if facts.get(key):
            values.append(str(facts[key]))
    for affix in facts.get("affixes") or []:
        if affix.get("name"):
            values.append(str(affix["name"]))
    tokens: set[str] = set()
    for value in values:
        for token in re.findall(r"[0-9A-Za-z가-힣一-龥ぁ-んァ-ン]+", value):
            token = token.strip()
            if len(token) >= 2:
                tokens.add(token)
    return tokens


def default_lead_sentence(facts: dict[str, Any]) -> str:
    intent = facts.get("intent")
    if intent == "character_basic_info":
        return "공식 데이터 기준 기본 프로필입니다."
    if intent == "character_constellation":
        return "공식 데이터 기준 별자리 정보입니다."
    if intent == "character_talent":
        return "공식 데이터 기준 특성 정보입니다."
    if intent == "weapon_basic_info":
        return "공식 데이터 기준 무기 정보입니다."
    if intent == "reliquary_effect_lookup":
        return "공식 데이터 기준 세트 효과입니다."
    return "공식 데이터 기준으로 확인한 내용입니다."


def ollama_chat(
    messages: list[dict[str, str]],
    *,
    model: str = DEFAULT_OLLAMA_MODEL,
    base_url: str = DEFAULT_OLLAMA_URL,
    timeout: float = 60.0,
    temperature: float = 0.2,
    think: bool = False,
    num_predict: int = 384,
) -> dict[str, Any]:
    url = base_url.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "think": think,
        "options": {
            "temperature": temperature,
            "num_predict": num_predict,
        },
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
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
    content = strip_thinking_blocks(str((data.get("message") or {}).get("content") or "")).strip()
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


def strip_thinking_blocks(content: str) -> str:
    cleaned = re.sub(r"<think>.*?</think>", "", content, flags=re.IGNORECASE | re.DOTALL)
    if "</think>" in cleaned.casefold():
        cleaned = re.sub(r"(?is)^.*?</think>\s*", "", cleaned)
    cleaned = re.sub(r"(?is)<think>.*$", "", cleaned)
    return cleaned


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
