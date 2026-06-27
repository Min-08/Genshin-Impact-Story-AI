from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.io import write_json
from genshin_lore_db.search_engine.engine import LoreSearchEngine
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL
from genshin_lore_db.search_engine.llm import build_reasoning_prompt
from genshin_lore_db.search_engine.qa import answer_question
from genshin_lore_db.search_engine.router import route_query


def main() -> int:
    parser = argparse.ArgumentParser(description="Developer CLI for the Genshin lore search engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("query")
    route_parser.add_argument("--out", help="JSON 결과를 저장할 경로")

    answer_parser = subparsers.add_parser("answer")
    answer_parser.add_argument("query")
    answer_parser.add_argument("--no-llm", action="store_true", help="로컬 Llama 없이 템플릿 답변만 생성")
    answer_parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama 모델 이름")
    answer_parser.add_argument("--out", help="JSON 결과를 저장할 경로")
    answer_parser.add_argument("--text", action="store_true", help="최종 답변 텍스트만 출력")

    for command in ["search", "investigate"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("query")
        sub.add_argument("--limit", type=int, default=20 if command == "search" else 40)
        sub.add_argument("--language", help="ko, en, ja, zh-Hans, und")
        sub.add_argument("--category", help="예: 여행 기록, 아카이브, 캐릭터")
        sub.add_argument("--content-type", help="예: quest, book, avatar")
        sub.add_argument("--include-textmap", action="store_true", default=command == "investigate")
        sub.add_argument("--out", help="JSON 결과를 저장할 경로")
        sub.add_argument("--prompt-out", help="investigate 결과에서 LLM 프롬프트 패키지를 저장할 경로")

    args = parser.parse_args()
    if args.command == "route":
        result = route_query(args.query).to_dict()
    elif args.command == "answer":
        result = answer_question(ROOT, args.query, use_llm=not args.no_llm, model=args.model)
    else:
        engine = LoreSearchEngine.open(ROOT)
    if args.command == "search":
        result = engine.search(
            args.query,
            limit=args.limit,
            language=args.language,
            category=args.category,
            content_type=args.content_type,
            include_textmap=args.include_textmap,
        )
    elif args.command == "investigate":
        result = engine.investigate(
            args.query,
            limit=args.limit,
            language=args.language,
            category=args.category,
            content_type=args.content_type,
            include_textmap=args.include_textmap,
        )
        if args.prompt_out:
            write_json(Path(args.prompt_out), build_reasoning_prompt(result))
    if args.out:
        write_json(Path(args.out), result)
    if args.command == "answer" and args.text:
        sys.stdout.buffer.write((str(result.get("final_answer") or "") + "\n").encode("utf-8"))
    else:
        sys.stdout.buffer.write((json.dumps(result, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
