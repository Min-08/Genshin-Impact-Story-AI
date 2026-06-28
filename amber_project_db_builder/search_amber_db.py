from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from amber_project_db_builder.pipeline.project_amber_v2 import search_project_amber_v2


def main() -> int:
    parser = argparse.ArgumentParser(description="Search the generated Project Amber SQLite DB.")
    parser.add_argument("query")
    parser.add_argument("--db", default=str(ROOT / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"))
    parser.add_argument("--language", help="Filter language, e.g. ko, en, ja, zh-Hans.")
    parser.add_argument("--content-type", help="Filter content type, e.g. book, quest, avatar, weapon.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--mode", choices=["unicode", "trigram"], default="unicode")
    parser.add_argument("--include-textmap", action="store_true")
    parser.add_argument("--json", action="store_true", help="Print full JSON rows.")
    args = parser.parse_args()

    rows = search_project_amber_v2(
        Path(args.db),
        args.query,
        language=args.language,
        content_type=args.content_type,
        limit=args.limit,
        mode=args.mode,
        include_textmap=args.include_textmap,
    )
    if args.json:
        sys.stdout.buffer.write((json.dumps(rows, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return 0

    for index, row in enumerate(rows, start=1):
        title = row.get("title") or row.get("key") or ""
        language = row.get("language") or ""
        content_type = row.get("content_type") or row.get("source") or ""
        unit_id = row.get("unit_id") or row.get("entry_id") or ""
        text = str(row.get("text") or row.get("value") or "").replace("\n", " ")
        if len(text) > 180:
            text = text[:177] + "..."
        print(f"{index}. [{language}/{content_type}] {title}")
        print(f"   {unit_id}")
        print(f"   {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
