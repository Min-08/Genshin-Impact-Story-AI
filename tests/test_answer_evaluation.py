from __future__ import annotations

from pathlib import Path

from genshin_lore_db.search_engine.answer_evaluation import evaluate_answer_engine, load_answer_evaluation_set
from genshin_lore_db.search_engine.qa import answer_question


ROOT = Path(__file__).resolve().parents[1]


def test_answer_evaluation_set_loads() -> None:
    evaluation_set = load_answer_evaluation_set(ROOT / "config" / "answer_evaluation_set.json")

    assert evaluation_set["version"] == "0.6.2"
    assert len(evaluation_set["cases"]) >= 24
    assert {
        "reliquary_effect_lookup",
        "weapon_basic_info",
        "character_basic_info",
        "unsupported",
    } <= {case["expected_intent"] for case in evaluation_set["cases"]}


def test_answer_output_includes_stable_metadata() -> None:
    result = answer_question(ROOT, "푸리나 기본정보", use_llm=False)

    assert result["canonical_id"] == "project_amber:avatar:10000089"
    assert result["content_type"] == "avatar"
    assert result["item_id"] == "10000089"


def test_answer_evaluator_detects_required_and_forbidden_fragment_failures() -> None:
    evaluation_set = {
        "version": "test",
        "cases": [
            {
                "id": "bad_fragments",
                "query": "푸리나 기본정보",
                "expected_route": "basic_lookup",
                "expected_intent": "character_basic_info",
                "expected_content_type": "avatar",
                "expected_canonical_id": "project_amber:avatar:10000089",
                "expected_item_id": "10000089",
                "required_fragments": ["평가셋에 없는 문장"],
                "forbidden_fragments": ["푸리나"],
            }
        ],
        "thresholds": {"case_passed": 1.0},
    }

    report = evaluate_answer_engine(ROOT, evaluation_set, use_llm=False)
    case = report["cases"][0]

    assert not case["passed"]
    assert case["missing_required_fragments"] == ["평가셋에 없는 문장"]
    assert case["present_forbidden_fragments"] == ["푸리나"]
    assert report["aggregate"]["case_passed"] == 0.0


def test_answer_evaluator_keeps_unsupported_questions_unsupported() -> None:
    evaluation_set = {
        "version": "test",
        "cases": [
            {
                "id": "unsupported",
                "query": "세계수와 기억 조작 가능성",
                "expected_route": "research",
                "expected_intent": "unsupported",
                "expected_content_type": None,
                "expected_canonical_id": None,
                "expected_item_id": None,
                "required_fragments": ["지원하는 정답형 QA 대상을 찾지 못했습니다"],
                "forbidden_fragments": ["5성 캐릭터입니다"],
            }
        ],
        "thresholds": {"case_passed": 1.0},
    }

    report = evaluate_answer_engine(ROOT, evaluation_set, use_llm=False)
    case = report["cases"][0]

    assert case["passed"]
    assert case["actual"]["intent"] == "unsupported"
    assert case["actual"]["content_type"] is None
