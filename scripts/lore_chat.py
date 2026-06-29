from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL
from genshin_lore_db.search_engine.terminal import run_terminal_qa


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive terminal QA for the Genshin lore search engine.")
    parser.add_argument("--no-llm", action="store_true", help="로컬 LLM 재작성 없이 템플릿 답변만 출력")
    parser.add_argument("--no-route", action="store_true", help="질문 라우팅 상태 표시를 끔")
    parser.add_argument("--auto-start-llm", dest="auto_start_llm", action="store_true", default=True, help="Ollama 서버를 자동 시작")
    parser.add_argument("--no-auto-start-llm", action="store_true", help="Ollama 서버를 자동 시작하지 않음")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama 모델 이름")
    parser.add_argument("--json", action="store_true", help="최종 답변 대신 전체 JSON 결과를 출력")
    parser.add_argument("--once", help="대화형 루프 없이 질문 한 번만 실행하고 종료")
    args = parser.parse_args()

    return run_terminal_qa(
        ROOT,
        use_llm=not args.no_llm,
        use_routing=not args.no_route,
        model=args.model,
        json_output=args.json,
        once=args.once,
        auto_start_llm=args.auto_start_llm and not args.no_auto_start_llm,
    )


if __name__ == "__main__":
    raise SystemExit(main())
