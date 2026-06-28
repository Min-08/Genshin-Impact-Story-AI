from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL
from genshin_lore_db.search_engine.qa import answer_question


EXIT_COMMANDS = {"exit", "quit", "q", ":exit", ":quit", ":q"}
HELP_COMMANDS = {"help", "?", ":help"}


def run_terminal_qa(
    root: Path | str,
    *,
    use_llm: bool = True,
    use_routing: bool = True,
    model: str = DEFAULT_OLLAMA_MODEL,
    json_output: bool = False,
    once: str | None = None,
) -> int:
    root_path = Path(root).resolve()
    configure_utf8_stdio()

    if once:
        result = answer_terminal_query(
            root_path,
            once,
            use_llm=use_llm,
            use_routing=use_routing,
            model=model,
        )
        emit_result(result, json_output=json_output)
        return 0

    print("Genshin Lore QA terminal")
    print(f"LLM: {'on' if use_llm else 'off'} | routing: {'on' if use_routing else 'off'} | model: {model}")
    print("질문을 입력하세요. 종료하려면 exit, quit, q를 입력하세요.")
    print()

    while True:
        try:
            query = input("질문> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not query:
            continue
        if query.casefold() in EXIT_COMMANDS:
            return 0
        if query.casefold() in HELP_COMMANDS:
            print_help()
            continue

        try:
            result = answer_terminal_query(
                root_path,
                query,
                use_llm=use_llm,
                use_routing=use_routing,
                model=model,
            )
        except Exception as exc:  # noqa: BLE001 - terminal loop should keep running.
            print(f"[error] {type(exc).__name__}: {exc}", file=sys.stderr)
            continue

        emit_result(result, json_output=json_output)


def answer_terminal_query(
    root: Path,
    query: str,
    *,
    use_llm: bool,
    use_routing: bool,
    model: str,
) -> dict[str, Any]:
    result = answer_question(root, query, use_llm=use_llm, model=model)
    if not use_routing:
        result.pop("route", None)
    return result


def emit_result(result: dict[str, Any], *, json_output: bool) -> None:
    if json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(status_line(result))
    print(str(result.get("final_answer") or "").strip())
    print()


def status_line(result: dict[str, Any]) -> str:
    parts = []
    route = result.get("route")
    if isinstance(route, dict):
        confidence = route.get("confidence")
        if isinstance(confidence, (int, float)):
            parts.append(f"route={route.get('mode', 'unknown')}:{confidence:.2f}")
        else:
            parts.append(f"route={route.get('mode', 'unknown')}")
    parts.append(f"intent={result.get('intent', 'unknown')}")
    parts.append(f"llm={llm_status(result.get('llm'))}")
    return "[" + " | ".join(parts) + "]"


def llm_status(llm: Any) -> str:
    if not isinstance(llm, dict):
        return "unknown"
    if not llm.get("enabled"):
        return "off"
    if llm.get("used"):
        return "used"
    error = llm.get("error") or {}
    if isinstance(error, dict) and error.get("type"):
        return f"fallback:{error['type']}"
    if llm.get("ok"):
        return "fallback:validation"
    return "fallback"


def print_help() -> None:
    print("사용법: 질문을 그대로 입력하면 됩니다.")
    print("지원 범위: 성유물 효과, 무기 기본정보/효과, 캐릭터 기본정보")
    print("종료: exit, quit, q")
    print()


def configure_utf8_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
