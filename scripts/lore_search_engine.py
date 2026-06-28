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
from genshin_lore_db.search_engine.qa import answer_question, route_answer_query
from genshin_lore_db.search_engine.terminal import run_terminal_qa
from genshin_lore_db.search_engine.v2_engine import ProjectAmberV2SearchEngine


def open_developer_search_engine(root: Path, db_version: str, db: str | None = None):
    db_root = Path(db) if db else root
    if db_version == "v1":
        return LoreSearchEngine.open(db_root)
    return ProjectAmberV2SearchEngine.open(db_root)


def main() -> int:
    parser = argparse.ArgumentParser(description="Developer CLI for the Genshin lore search engine.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    route_parser = subparsers.add_parser("route")
    route_parser.add_argument("query")
    route_parser.add_argument("--no-llm", action="store_true", help="로컬 LLM semantic parser 없이 규칙/DB 기반 라우팅만 실행")
    route_parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama 모델 이름")
    route_parser.add_argument("--out", help="JSON 결과를 저장할 경로")

    answer_parser = subparsers.add_parser("answer")
    answer_parser.add_argument("query")
    answer_parser.add_argument("--no-llm", action="store_true", help="로컬 LLM 없이 템플릿 답변만 생성")
    answer_parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama 모델 이름")
    answer_parser.add_argument("--out", help="JSON 결과를 저장할 경로")
    answer_parser.add_argument("--text", action="store_true", help="최종 답변 텍스트만 출력")

    chat_parser = subparsers.add_parser("chat")
    chat_parser.add_argument("--no-llm", action="store_true", help="로컬 LLM 재작성 없이 템플릿 답변만 출력")
    chat_parser.add_argument("--no-route", action="store_true", help="질문 라우팅 상태 표시를 끔")
    chat_parser.add_argument("--no-auto-start-llm", action="store_true", help="Ollama 서버를 자동 시작하지 않음")
    chat_parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama 모델 이름")
    chat_parser.add_argument("--json", action="store_true", help="최종 답변 대신 전체 JSON 결과를 출력")
    chat_parser.add_argument("--once", help="대화형 루프 없이 질문 한 번만 실행하고 종료")

    for command in ["search", "investigate"]:
        sub = subparsers.add_parser(command)
        sub.add_argument("query")
        sub.add_argument("--db", help="Override the default search DB path")
        sub.add_argument("--db-version", choices=["v2", "v1"], default="v2", help="Search DB version to use")
        sub.add_argument("--limit", type=int, default=20 if command == "search" else 40)
        sub.add_argument("--language", help="ko, en, ja, zh-Hans, und")
        sub.add_argument("--category", help="예: 여행 기록, 아카이브, 캐릭터")
        sub.add_argument("--content-type", help="예: quest, book, avatar")
        sub.add_argument("--mode", choices=["unicode", "trigram"], default="unicode")
        sub.add_argument("--include-textmap", action="store_true", default=command == "investigate")
        sub.add_argument("--out", help="JSON 결과를 저장할 경로")
        sub.add_argument("--prompt-out", help="investigate 결과에서 LLM 프롬프트 패키지를 저장할 경로")

    args = parser.parse_args()
    if args.command == "chat":
        return run_terminal_qa(
            ROOT,
            use_llm=not args.no_llm,
            use_routing=not args.no_route,
            model=args.model,
            json_output=args.json,
            once=args.once,
            auto_start_llm=not args.no_auto_start_llm,
        )

    if args.command == "route":
        result = route_answer_query(ROOT, args.query, use_llm=not args.no_llm, model=args.model)
    elif args.command == "answer":
        result = answer_question(ROOT, args.query, use_llm=not args.no_llm, model=args.model)
    else:
        try:
            engine = open_developer_search_engine(ROOT, args.db_version, args.db)
        except (FileNotFoundError, IsADirectoryError) as exc:
            sys.stderr.write(str(exc) + "\n")
            return 2
    if args.command == "search":
        search_kwargs = {
            "limit": args.limit,
            "language": args.language,
            "category": args.category,
            "content_type": args.content_type,
            "include_textmap": args.include_textmap,
        }
        if args.db_version == "v2":
            search_kwargs["mode"] = args.mode
        result = engine.search(args.query, **search_kwargs)
    elif args.command == "investigate":
        investigate_kwargs = {
            "limit": args.limit,
            "language": args.language,
            "category": args.category,
            "content_type": args.content_type,
            "include_textmap": args.include_textmap,
        }
        if args.db_version == "v2":
            investigate_kwargs["mode"] = args.mode
        result = engine.investigate(args.query, **investigate_kwargs)
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
