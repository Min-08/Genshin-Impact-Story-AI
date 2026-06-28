from __future__ import annotations

from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL, safe_lead_sentence, strip_thinking_blocks
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
