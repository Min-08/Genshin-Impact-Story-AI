from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence

from .dimbreath import crawl_dimbreath_textmaps
from .normalize import build_canonical
from .pipeline.project_amber_v2 import build_project_amber_v2
from .project_amber import crawl_project_amber
from .project_amber_deep import crawl_project_amber_deep
from .search_engine.evidence_store import DEFAULT_WORKSPACE_ID, EvidenceStore
from .search_engine.source_reader import EVIDENCE_ROLES, SOURCE_LEVELS, ProjectAmberV2SourceReader
from .search_engine.v2_engine import ProjectAmberV2SearchEngine


DEFAULT_MAX_UNITS = 100


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    try:
        if args.command in {
            "crawl-project-amber",
            "crawl-project-amber-deep",
            "crawl-dimbreath-textmap",
            "build-canonical",
            "build-project-amber-v2",
        }:
            return run_pipeline_command(args, root)
        if args.command == "search":
            return run_search_command(args, root)
        if args.command == "pin-evidence":
            return run_pin_evidence_command(args, root)
        if args.command == "evidence":
            return run_evidence_command(args, root)
        return run_source_reader_command(args, root)
    except (FileNotFoundError, IsADirectoryError, ValueError) as exc:
        return emit_error("command_failed", str(exc), json_output=bool(getattr(args, "json", False)))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="genshin-lore-db")
    parser.add_argument("--root", default=".", help="Project root directory or Project Amber v2 SQLite DB path")
    subparsers = parser.add_subparsers(dest="command", required=True)

    amber = subparsers.add_parser("crawl-project-amber", help="Fetch Project Amber API data")
    amber.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    amber.add_argument("--content-types", nargs="+", help="Project Amber content types")
    amber.add_argument("--limit", type=int, help="Limit list items per language/content type")
    amber.add_argument("--detail-limit", type=int, help="Limit fetched details per language/content type")
    amber.add_argument("--skip-details", action="store_true", help="Only fetch list endpoints")
    amber.add_argument(
        "--include-unreleased",
        action="store_true",
        default=None,
        help="Include entries marked as unreleased/future",
    )
    amber.add_argument("--force", action="store_true", help="Refetch cached files")
    amber.add_argument("--sleep", type=float, default=0.25, help="Delay between requests")

    amber_deep = subparsers.add_parser("crawl-project-amber-deep", help="Fetch Project Amber secondary text endpoints")
    amber_deep.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    amber_deep.add_argument("--content-types", nargs="+", help="Project Amber content types with deep text")
    amber_deep.add_argument("--limit", type=int, help="Limit detail records per language/content type")
    amber_deep.add_argument("--target-limit", type=int, help="Limit secondary targets per detail record")
    amber_deep.add_argument("--force", action="store_true", help="Refetch cached files")
    amber_deep.add_argument("--sleep", type=float, default=0.25, help="Delay between requests")

    textmap = subparsers.add_parser("crawl-dimbreath-textmap", help="Fetch Dimbreath TextMap files")
    textmap.add_argument("--languages", nargs="+", help="Language keys from config, e.g. ko zh-Hans ja en")
    textmap.add_argument("--force", action="store_true", help="Refetch cached files")
    textmap.add_argument("--sleep", type=float, default=0.5, help="Delay between requests")

    subparsers.add_parser("build-canonical", help="Build normalized JSONL files from RAW data")
    subparsers.add_parser("build-project-amber-v2", help="Build Project Amber v2 readable/canonical/search outputs")

    search = subparsers.add_parser("search", help="Search Project Amber v2 and optionally attach source windows")
    search.add_argument("query")
    search.add_argument("--limit", type=positive_int, default=20)
    search.add_argument("--language", help="ko, en, ja, zh-Hans, und")
    search.add_argument("--category", help="Legacy category filter; ignored by Project Amber v2")
    search.add_argument("--content-type", help="quest, book, avatar, material, weapon, reliquary")
    search.add_argument("--mode", choices=["unicode", "trigram"], default="unicode")
    search.add_argument("--include-textmap", action="store_true")
    search.add_argument("--with-window", action="store_true", help="Attach read-window output for each result")
    search.add_argument("--before", type=non_negative_int, default=3, help="Context units before each result")
    search.add_argument("--after", type=non_negative_int, default=3, help="Context units after each result")
    search.add_argument("--json", action="store_true", help="Emit machine-readable JSON")

    window = subparsers.add_parser("read-window", help="Read context around a Project Amber v2 text unit")
    window.add_argument("unit_id")
    window.add_argument("--before", type=non_negative_int, default=5)
    window.add_argument("--after", type=non_negative_int, default=5)
    window.add_argument("--language", help="Require the window language to match this value")
    window.add_argument("--json", action="store_true")

    document = subparsers.add_parser("read-document", help="Read a Project Amber v2 document")
    document.add_argument("document_id")
    document.add_argument("--json", action="store_true")
    document.add_argument("--max-units", type=non_negative_int, default=DEFAULT_MAX_UNITS)
    document.add_argument("--no-units", action="store_true")

    section = subparsers.add_parser("read-section", help="Read a Project Amber v2 section")
    section.add_argument("section_id")
    section.add_argument("--json", action="store_true")
    section.add_argument("--max-units", type=non_negative_int, default=DEFAULT_MAX_UNITS)
    section.add_argument("--no-units", action="store_true")

    parallel = subparsers.add_parser("read-parallel", help="Read parallel language units for a text unit")
    parallel.add_argument("unit_id")
    parallel.add_argument("--languages", default="ko,en,ja,zh-Hans")
    parallel.add_argument("--json", action="store_true")

    pin = subparsers.add_parser("pin-evidence", help="Pin a unit character span into the evidence store")
    pin.add_argument("--unit-id", required=True)
    pin.add_argument("--start", type=non_negative_int, required=True)
    pin.add_argument("--end", type=non_negative_int, required=True)
    pin.add_argument("--role", required=True, help=f"One of: {', '.join(sorted(EVIDENCE_ROLES))}")
    pin.add_argument("--source-level", default="L0", help=f"One of: {', '.join(sorted(SOURCE_LEVELS))}")
    pin.add_argument("--note")
    pin.add_argument("--hypothesis-id", dest="hypothesis_ids", action="append", default=[])
    pin.add_argument("--workspace", default=DEFAULT_WORKSPACE_ID)
    pin.add_argument("--json", action="store_true")

    evidence = subparsers.add_parser("evidence", help="Browse saved evidence pins")
    evidence_subparsers = evidence.add_subparsers(dest="evidence_command", required=True)
    evidence_list = evidence_subparsers.add_parser("list", help="List evidence pins")
    evidence_list.add_argument("--workspace", default=DEFAULT_WORKSPACE_ID)
    evidence_list.add_argument("--role", help="Filter by evidence role")
    evidence_list.add_argument("--query", help="Filter by text, title, note, or ids")
    evidence_list.add_argument("--json", action="store_true")
    evidence_show = evidence_subparsers.add_parser("show", help="Show one evidence pin")
    evidence_show.add_argument("evidence_id")
    evidence_show.add_argument("--workspace", default=DEFAULT_WORKSPACE_ID)
    evidence_show.add_argument("--json", action="store_true")

    return parser


def run_pipeline_command(args: argparse.Namespace, root: Path) -> int:
    if args.command == "crawl-project-amber":
        report = crawl_project_amber(
            root,
            languages=args.languages,
            content_types=args.content_types,
            limit=args.limit,
            detail_limit=args.detail_limit,
            skip_details=args.skip_details,
            include_unreleased=args.include_unreleased,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "crawl-project-amber-deep":
        report = crawl_project_amber_deep(
            root,
            languages=args.languages,
            content_types=args.content_types,
            limit=args.limit,
            target_limit=args.target_limit,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "crawl-dimbreath-textmap":
        report = crawl_dimbreath_textmaps(
            root,
            languages=args.languages,
            force=args.force,
            sleep_seconds=args.sleep,
        )
    elif args.command == "build-canonical":
        report = build_canonical(root)
    elif args.command == "build-project-amber-v2":
        report = build_project_amber_v2(root)
    else:
        raise AssertionError(args.command)

    print(report)
    return 0


def run_search_command(args: argparse.Namespace, root: Path) -> int:
    engine = ProjectAmberV2SearchEngine.open(root)
    result = engine.search(
        args.query,
        limit=args.limit,
        language=args.language,
        category=args.category,
        content_type=args.content_type,
        include_textmap=args.include_textmap,
        mode=args.mode,
        with_window=args.with_window,
        window_before=args.before,
        window_after=args.after,
    )
    if args.json:
        emit_json(result)
    else:
        emit_text(format_search(result, with_window=args.with_window))
    return 0


def run_pin_evidence_command(args: argparse.Namespace, root: Path) -> int:
    reader = ProjectAmberV2SourceReader.open(root)
    evidence = reader.pin_unit_evidence(
        args.unit_id,
        args.start,
        args.end,
        role=args.role,
        source_level=args.source_level,
        note=args.note,
        hypothesis_ids=args.hypothesis_ids,
    )
    if evidence is None:
        return emit_error(
            "unit_not_found",
            f"Unit not found: {args.unit_id}",
            json_output=args.json,
            resource_id=args.unit_id,
        )
    store = EvidenceStore.open(root, workspace_id=args.workspace)
    saved = store.append(evidence)
    payload = {
        "ok": True,
        "created": saved["created"],
        "workspace_id": args.workspace,
        "path": saved["path"],
        "evidence_id": saved["record"]["evidence_id"],
        "evidence": saved["record"],
    }
    if args.json:
        emit_json(payload)
    else:
        emit_text(format_pin_result(payload))
    return 0


def run_evidence_command(args: argparse.Namespace, root: Path) -> int:
    store = EvidenceStore.open(root, workspace_id=args.workspace)
    if args.evidence_command == "list":
        records = store.list(role=args.role, query=args.query)
        payload = {
            "workspace_id": args.workspace,
            "path": str(store.path),
            "count": len(records),
            "evidence": records,
        }
        if args.json:
            emit_json(payload)
        else:
            emit_text(format_evidence_list(payload))
        return 0
    if args.evidence_command == "show":
        record = store.get(args.evidence_id)
        if record is None:
            return emit_error(
                "evidence_not_found",
                f"Evidence not found: {args.evidence_id}",
                json_output=args.json,
                resource_id=args.evidence_id,
            )
        if args.json:
            emit_json(record)
        else:
            emit_text(format_evidence_record(record))
        return 0
    raise AssertionError(args.evidence_command)


def run_source_reader_command(args: argparse.Namespace, root: Path) -> int:
    reader = ProjectAmberV2SourceReader.open(root)
    if args.command == "read-window":
        window = reader.read_window(args.unit_id, before=args.before, after=args.after)
        if window is None:
            return emit_error(
                "unit_not_found",
                f"Unit not found: {args.unit_id}",
                json_output=args.json,
                resource_id=args.unit_id,
            )
        if args.language and window.get("language") != args.language:
            return emit_error(
                "language_mismatch",
                f"Unit language is {window.get('language')!r}, expected {args.language!r}.",
                json_output=args.json,
                resource_id=args.unit_id,
            )
        return emit_payload(window, json_output=args.json, text=format_window(window))

    if args.command == "read-document":
        include_units = not args.no_units
        document = reader.read_document(args.document_id, include_units=include_units, max_units=args.max_units)
        if document is None:
            return emit_error(
                "document_not_found",
                f"Document not found: {args.document_id}",
                json_output=args.json,
                resource_id=args.document_id,
            )
        return emit_payload(document, json_output=args.json, text=format_document(document))

    if args.command == "read-section":
        include_units = not args.no_units
        section = reader.read_section(args.section_id, include_units=include_units, max_units=args.max_units)
        if section is None:
            return emit_error(
                "section_not_found",
                f"Section not found: {args.section_id}",
                json_output=args.json,
                resource_id=args.section_id,
            )
        return emit_payload(section, json_output=args.json, text=format_section(section))

    if args.command == "read-parallel":
        parallel = reader.read_parallel(args.unit_id, languages=parse_languages(args.languages))
        if parallel is None:
            return emit_error(
                "unit_not_found",
                f"Unit not found: {args.unit_id}",
                json_output=args.json,
                resource_id=args.unit_id,
            )
        return emit_payload(parallel, json_output=args.json, text=format_parallel(parallel))

    raise AssertionError(args.command)


def emit_payload(payload: dict[str, Any], *, json_output: bool, text: str) -> int:
    if json_output:
        emit_json(payload)
    else:
        emit_text(text)
    return 0


def emit_json(payload: Any) -> None:
    sys.stdout.buffer.write((json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def emit_text(text: str) -> None:
    sys.stdout.buffer.write((text.rstrip() + "\n").encode("utf-8"))


def emit_error(
    code: str,
    message: str,
    *,
    json_output: bool = False,
    resource_id: str | None = None,
) -> int:
    payload: dict[str, Any] = {"ok": False, "error": {"code": code, "message": message}}
    if resource_id is not None:
        payload["error"]["id"] = resource_id
    if json_output:
        emit_json(payload)
    else:
        sys.stderr.buffer.write((message.rstrip() + "\n").encode("utf-8"))
    return 2


def format_search(result: dict[str, Any], *, with_window: bool) -> str:
    lines = [f"Query: {result.get('query')}", f"Results: {len(result.get('results') or [])}", ""]
    for index, hit in enumerate(result.get("results") or [], start=1):
        score = hit.get("score")
        score_text = f" score={score}" if score is not None else ""
        lines.append(f"{index}. [{hit.get('language')}] {hit.get('title') or '(untitled)'}{score_text}")
        lines.append(f"   Unit: {hit.get('unit_id') or '(not source-readable)'}")
        lines.append(f"   Document: {hit.get('document_id') or '(none)'}")
        lines.append(f"   Canonical: {hit.get('canonical_id') or '(none)'}")
        text = hit.get("excerpt") or hit.get("text") or ""
        if text:
            lines.append(f"   Text: {truncate_one_line(text, 500)}")
        if with_window:
            window = hit.get("source_window")
            if window:
                lines.append("   Window:")
                lines.extend(f"     {line}" for line in compact_window_lines(window))
            else:
                error = hit.get("source_reader") or {}
                lines.append(f"   Window: unavailable ({error.get('code')}: {error.get('message')})")
        lines.append("")
    return "\n".join(lines)


def format_window(window: dict[str, Any]) -> str:
    lines = [
        f"Document: {window.get('document_id')}",
        f"Title: {window.get('document_title') or window.get('title') or '(untitled)'}",
        f"Language: {window.get('language')}",
        f"Unit: {window.get('center_unit_id')}",
        f"Section: {window.get('section_id') or '(none)'}",
    ]
    source_url = window.get("source_url")
    if source_url:
        lines.append(f"Source URL: {source_url}")
    lines.append("")
    lines.extend(format_unit_block("Before", window.get("before") or []))
    lines.extend(format_unit_block("Center", [window.get("center")] if window.get("center") else []))
    lines.extend(format_unit_block("After", window.get("after") or []))
    return "\n".join(lines)


def format_document(document: dict[str, Any]) -> str:
    lines = [
        f"Document: {document.get('document_id')}",
        f"Title: {document.get('title') or '(untitled)'}",
        f"Language: {document.get('language')}",
        f"Content Type: {document.get('content_type')}",
        f"Canonical: {document.get('canonical_id')}",
        f"Source URL: {document.get('source_url') or '(none)'}",
        f"Sections: {document.get('section_count', len(document.get('sections') or []))}",
        f"Units: {document.get('unit_count', len(document.get('units') or []))}",
        "",
    ]
    if "units" in document:
        lines.extend(format_unit_block("Units", document.get("units") or []))
        append_omission_note(lines, document)
    else:
        lines.append("[Sections]")
        for section in document.get("sections") or []:
            lines.append(f"{section.get('ordinal')}: {section.get('section_id')} - {section.get('title') or '(untitled)'}")
    return "\n".join(lines)


def format_section(section: dict[str, Any]) -> str:
    lines = [
        f"Section: {section.get('section_id')}",
        f"Document: {section.get('document_id')}",
        f"Title: {section.get('title') or '(untitled)'}",
        f"Document Title: {section.get('document_title') or '(untitled)'}",
        f"Language: {section.get('language')}",
        f"Content Type: {section.get('content_type')}",
        f"Canonical: {section.get('canonical_id')}",
        f"Source URL: {section.get('source_url') or '(none)'}",
        f"Units: {section.get('unit_count', len(section.get('units') or []))}",
        "",
    ]
    if "units" in section:
        lines.extend(format_unit_block("Units", section.get("units") or []))
        append_omission_note(lines, section)
    else:
        lines.append(section.get("text") or "")
    return "\n".join(lines)


def format_parallel(parallel: dict[str, Any]) -> str:
    lines = [
        f"Unit: {parallel.get('unit_id')}",
        f"Canonical: {parallel.get('canonical_id')}",
        f"Document Kind: {parallel.get('document_kind')}",
        f"Ordinal: {parallel.get('ordinal')}",
        "",
    ]
    for block in parallel.get("blocks") or []:
        lines.append(f"[{block.get('language')}]")
        if not block.get("found"):
            reason = block.get("reason")
            lines.append(f"(missing: {reason})" if reason else "(missing)")
        else:
            lines.append(f"Unit: {block.get('unit_id')}")
            source_url = block.get("source_url")
            if source_url:
                lines.append(f"Source URL: {source_url}")
            lines.append(str(block.get("text") or ""))
        lines.append("")
    return "\n".join(lines)


def format_pin_result(payload: dict[str, Any]) -> str:
    status = "saved" if payload.get("created") else "already exists"
    evidence = payload.get("evidence") or {}
    lines = [
        f"Evidence: {payload.get('evidence_id')}",
        f"Status: {status}",
        f"Workspace: {payload.get('workspace_id')}",
        f"Role: {evidence.get('role')}",
        f"Unit: {evidence.get('unit_id')}",
        f"Excerpt: {evidence.get('excerpt')}",
    ]
    note = evidence.get("note")
    if note:
        lines.append(f"Note: {note}")
    return "\n".join(lines)


def format_evidence_list(payload: dict[str, Any]) -> str:
    records = payload.get("evidence") or []
    lines = [
        f"Workspace: {payload.get('workspace_id')}",
        f"Count: {payload.get('count')}",
        "",
    ]
    if not records:
        lines.append("(none)")
        return "\n".join(lines)
    for record in records:
        lines.append(
            f"{record.get('evidence_id')} [{record.get('role')}] "
            f"{record.get('title') or '(untitled)'} / {record.get('language')}"
        )
        lines.append(f"  Unit: {record.get('unit_id') or '(document span)'}")
        lines.append(f"  Excerpt: {truncate_one_line(record.get('excerpt') or '', 180)}")
        if record.get("note"):
            lines.append(f"  Note: {truncate_one_line(record.get('note') or '', 180)}")
    return "\n".join(lines)


def format_evidence_record(record: dict[str, Any]) -> str:
    lines = [
        f"Evidence: {record.get('evidence_id')}",
        f"Workspace: {record.get('workspace_id')}",
        f"Role: {record.get('role')}",
        f"Source Level: {record.get('source_level')}",
        f"Document: {record.get('document_id')}",
        f"Unit: {record.get('unit_id') or '(document span)'}",
        f"Section: {record.get('section_id') or '(none)'}",
        f"Canonical: {record.get('canonical_id')}",
        f"Source URL: {record.get('source_url') or '(none)'}",
        f"Language: {record.get('language')}",
        f"Content Type: {record.get('content_type')}",
        f"Title: {record.get('title') or '(untitled)'}",
        f"Span: {record.get('start_char')}:{record.get('end_char')}",
        f"Created: {record.get('created_at')}",
        "",
        "[Excerpt]",
        str(record.get("excerpt") or ""),
    ]
    note = record.get("note")
    if note:
        lines.extend(["", "[Note]", str(note)])
    return "\n".join(lines)


def compact_window_lines(window: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for unit in window.get("units") or []:
        marker = "*" if unit.get("unit_id") == window.get("center_unit_id") else "-"
        lines.append(f"{marker} {unit.get('ordinal')} {unit.get('unit_id')}: {truncate_one_line(unit.get('text') or '', 220)}")
    return lines or ["(empty)"]


def format_unit_block(title: str, units: list[dict[str, Any]]) -> list[str]:
    lines = [f"[{title}]"]
    if not units:
        lines.append("(none)")
        lines.append("")
        return lines
    for unit in units:
        lines.append(f"{unit.get('ordinal')} {unit.get('unit_id')}")
        speaker = unit.get("speaker")
        if speaker:
            lines.append(f"Speaker: {speaker}")
        lines.append(str(unit.get("text") or ""))
        lines.append("")
    return lines


def append_omission_note(lines: list[str], payload: dict[str, Any]) -> None:
    total = int(payload.get("unit_count") or 0)
    included = int(payload.get("included_unit_count") or len(payload.get("units") or []))
    if total > included:
        lines.append(f"... {total - included} more units omitted by --max-units.")


def truncate_one_line(text: str, max_chars: int) -> str:
    cleaned = " ".join(str(text).split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def parse_languages(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def non_negative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return number


def positive_int(value: str) -> int:
    number = non_negative_int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


if __name__ == "__main__":
    raise SystemExit(main())
