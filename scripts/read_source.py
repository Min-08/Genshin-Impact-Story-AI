from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.search_engine.source_reader import EVIDENCE_ROLES, SOURCE_LEVELS, ProjectAmberV2SourceReader


def main() -> int:
    parser = argparse.ArgumentParser(description="Read Project Amber v2 source units, windows, and documents.")
    parser.add_argument("--db", type=Path, help="Override data/processed/search_v2/project_amber_search.sqlite3.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    search = subparsers.add_parser("search", help="Search Project Amber v2 text units.")
    search.add_argument("query")
    search.add_argument("--language")
    search.add_argument("--content-type")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--mode", choices=["unicode", "trigram"], default="unicode")
    search.add_argument("--include-textmap", action="store_true")

    unit = subparsers.add_parser("unit", help="Read one text unit by unit_id.")
    unit.add_argument("unit_id")

    window = subparsers.add_parser("window", help="Read a text unit with nearby units from the same document.")
    window.add_argument("unit_id")
    window.add_argument("--before", type=int, default=5)
    window.add_argument("--after", type=int, default=5)

    expand_window = subparsers.add_parser("expand-window", help="Expand an existing reading window on one side.")
    expand_window.add_argument("window_id")
    expand_window.add_argument("--direction", choices=["before", "after"], required=True)
    expand_window.add_argument("--amount", type=int, default=10)

    section = subparsers.add_parser("section", help="Read one section by section_id.")
    section.add_argument("section_id")
    section.add_argument("--no-units", action="store_true")

    document = subparsers.add_parser("document", help="Read one document by document_id.")
    document.add_argument("document_id")
    document.add_argument("--no-units", action="store_true")
    document.add_argument("--max-units", type=int)

    parallel = subparsers.add_parser("parallel", help="Read language parallels for a unit ordinal.")
    parallel.add_argument("unit_id")
    parallel.add_argument("--languages", default="ko,en,ja,zh-Hans")

    pin_document = subparsers.add_parser("pin-document", help="Pin a character span from a document as evidence.")
    pin_document.add_argument("document_id")
    add_pin_arguments(pin_document)

    pin_unit = subparsers.add_parser("pin-unit", help="Pin a character span from a text unit as evidence.")
    pin_unit.add_argument("unit_id")
    add_pin_arguments(pin_unit)

    args = parser.parse_args()
    reader = ProjectAmberV2SourceReader.open(args.db or ROOT)

    try:
        if args.command == "search":
            output = reader.find_exact(
                args.query,
                language=args.language,
                content_type=args.content_type,
                limit=args.limit,
                mode=args.mode,
                include_textmap=args.include_textmap,
            )
        elif args.command == "unit":
            output = reader.read_unit(args.unit_id)
        elif args.command == "window":
            output = reader.read_window(args.unit_id, before=args.before, after=args.after)
        elif args.command == "expand-window":
            output = reader.expand_window(args.window_id, direction=args.direction, amount=args.amount)
        elif args.command == "section":
            output = reader.read_section(args.section_id, include_units=not args.no_units)
        elif args.command == "document":
            output = reader.read_document(args.document_id, include_units=not args.no_units, max_units=args.max_units)
        elif args.command == "parallel":
            languages = [item.strip() for item in args.languages.split(",") if item.strip()]
            output = reader.read_parallel(args.unit_id, languages=languages)
        elif args.command == "pin-document":
            output = reader.pin_evidence(
                args.document_id,
                args.start_char,
                args.end_char,
                role=args.role,
                source_level=args.source_level,
                note=args.note,
                hypothesis_ids=parse_csv(args.hypothesis_ids),
            )
        elif args.command == "pin-unit":
            output = reader.pin_unit_evidence(
                args.unit_id,
                args.start_char,
                args.end_char,
                role=args.role,
                source_level=args.source_level,
                note=args.note,
                hypothesis_ids=parse_csv(args.hypothesis_ids),
            )
        else:
            parser.error(f"Unsupported command: {args.command}")
    except ValueError as exc:
        parser.error(str(exc))

    if output is None:
        return 2
    sys.stdout.buffer.write((json.dumps(output, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


def add_pin_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--start-char", type=int, required=True)
    parser.add_argument("--end-char", type=int, required=True)
    parser.add_argument("--role", choices=sorted(EVIDENCE_ROLES), required=True)
    parser.add_argument("--source-level", choices=sorted(SOURCE_LEVELS), default="L0")
    parser.add_argument("--note")
    parser.add_argument("--hypothesis-ids", default="")


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
