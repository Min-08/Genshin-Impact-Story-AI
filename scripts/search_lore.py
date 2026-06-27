from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.pipeline.project_amber_v2 import search_project_amber_v2
from genshin_lore_db.rag_assets import search_lore


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--db")
    parser.add_argument("--db-version", choices=["v1", "v2"], default="v1")
    parser.add_argument("--language", help="ko, en, ja, zh-Hans, und")
    parser.add_argument("--category", help="v1 category filter, for example travel_log or archive")
    parser.add_argument("--content-type", help="content type filter, for example quest, book, avatar")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mode", choices=["unicode", "trigram"], default="unicode")
    parser.add_argument("--include-textmap", action="store_true")
    args = parser.parse_args()

    if args.db_version == "v2":
        db_path = Path(args.db) if args.db else ROOT / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
        rows = search_project_amber_v2(
            db_path,
            args.query,
            language=args.language,
            content_type=args.content_type,
            limit=args.limit,
            mode=args.mode,
            include_textmap=args.include_textmap,
        )
    else:
        db_path = Path(args.db) if args.db else ROOT / "data" / "processed" / "search" / "lore_search.sqlite3"
        rows = search_lore(
            db_path,
            args.query,
            language=args.language,
            category=args.category,
            content_type=args.content_type,
            limit=args.limit,
            mode=args.mode,
            include_textmap=args.include_textmap,
        )

    for row in rows:
        print(json.dumps(row, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
