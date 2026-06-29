from __future__ import annotations

from genshin_lore_db.search_engine.local_llm import (
    DEFAULT_OLLAMA_MODEL,
    ensure_local_llm_ready,
    safe_lead_sentence,
    strip_thinking_blocks,
)
from genshin_lore_db.search_engine.semantic import normalize_semantic_parse, parse_semantic_response


def test_default_ollama_model_uses_qwen3() -> None:
    assert DEFAULT_OLLAMA_MODEL == "qwen3:4b-instruct"


def test_strip_thinking_blocks_removes_qwen_reasoning() -> None:
    content = "<think>draft reasoning</think>\n최종 답변입니다."

    assert strip_thinking_blocks(content) == "\n최종 답변입니다."


def test_strip_thinking_blocks_handles_stray_closing_tag() -> None:
    content = "draft reasoning without opening tag</think>\n최종 답변입니다."

    assert strip_thinking_blocks(content) == "최종 답변입니다."


def test_safe_lead_sentence_rejects_fact_like_sentence() -> None:
    facts = {"intent": "character_basic_info", "name": "푸리나", "weapon_type": "한손검"}

    assert safe_lead_sentence("푸리나는 5성 물 원소 캐릭터입니다.", facts) == "공식 데이터 기준 기본 프로필입니다."
    assert safe_lead_sentence("한손검을 사용하는 캐릭터 정보입니다.", facts) == "공식 데이터 기준 기본 프로필입니다."


def test_safe_lead_sentence_accepts_generic_sentence() -> None:
    facts = {"intent": "weapon_basic_info"}

    assert safe_lead_sentence("공식 데이터로 확인한 무기 정보를 정리합니다.", facts) == "공식 데이터로 확인한 무기 정보를 정리합니다."


def test_parse_semantic_response_accepts_markdown_json() -> None:
    parsed = parse_semantic_response(
        '```json\n{"schema_version":"semantic_parse.v0.1","route":"basic_lookup","intent":"character_basic_info","entities":[{"surface":"아야카","content_type_hint":"avatar","confidence":0.9}],"requested_format":"paragraph","confidence":0.8}\n```'
    )

    assert parsed["ok"]
    normalized = normalize_semantic_parse(parsed["parse"])
    assert normalized["route"] == "basic_lookup"
    assert normalized["entities"][0]["surface"] == "아야카"


def test_parse_semantic_response_rejects_invalid_json() -> None:
    parsed = parse_semantic_response("분류 결과: basic_lookup")

    assert not parsed["ok"]
    assert parsed["error"]["type"] == "semantic_parse_invalid_json"


def test_ensure_local_llm_ready_reports_available(monkeypatch) -> None:
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_model_available", lambda *_args, **_kwargs: True)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL)

    assert status["available"] is True
    assert status["status"] == "available"
    assert status["server_reachable"] is True
    assert status["model_available"] is True


def test_ensure_local_llm_ready_auto_starts_when_possible(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.find_ollama_executable", lambda: "ollama")
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.start_ollama_server", lambda _path: calls.append("start") or True)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.wait_for_ollama", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_model_available", lambda *_args, **_kwargs: True)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL, auto_start=True)

    assert status["available"] is True
    assert status["status"] == "available"
    assert status["auto_start_attempted"] is True
    assert status["auto_started"] is True
    assert calls == ["start"]


def test_ensure_local_llm_ready_starts_windows_app_when_serve_does_not_become_ready(monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.find_ollama_executable", lambda: "ollama")
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.find_ollama_app_executable", lambda: "ollama app.exe")
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.start_ollama_server", lambda _path: calls.append("serve") or True)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.start_ollama_app", lambda _path: calls.append("app") or True)

    wait_results = iter([False, True])
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.wait_for_ollama", lambda *_args, **_kwargs: next(wait_results))
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_model_available", lambda *_args, **_kwargs: True)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL, auto_start=True)

    assert status["available"] is True
    assert status["status"] == "available"
    assert status["auto_start_attempted"] is True
    assert status["app_start_attempted"] is True
    assert status["app_started"] is True
    assert calls == ["serve", "app"]


def test_ensure_local_llm_ready_reports_missing_executable(monkeypatch) -> None:
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.find_ollama_executable", lambda: None)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL, auto_start=True)

    assert status["available"] is False
    assert status["status"] == "ollama_missing"
    assert status["auto_start_attempted"] is False
    assert "Ollama" in status["message"]


def test_ensure_local_llm_ready_reports_missing_model(monkeypatch) -> None:
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_model_available", lambda *_args, **_kwargs: False)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL)

    assert status["available"] is False
    assert status["status"] == "model_missing"
    assert status["model_available"] is False
    assert status["pull_command"] == "ollama pull qwen3:4b-instruct"
    assert "ollama pull qwen3:4b-instruct" in status["message"]


def test_ensure_local_llm_ready_no_auto_start_does_not_start(monkeypatch) -> None:
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.ollama_api_reachable", lambda *_args, **_kwargs: False)
    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.find_ollama_executable", lambda: "ollama")

    def fail_start(_path: str) -> bool:
        raise AssertionError("start_ollama_server should not be called")

    monkeypatch.setattr("genshin_lore_db.search_engine.local_llm.start_ollama_server", fail_start)

    status = ensure_local_llm_ready(model=DEFAULT_OLLAMA_MODEL, auto_start=False)

    assert status["available"] is False
    assert status["status"] == "server_unavailable"
    assert status["auto_start_attempted"] is False
