from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from genshin_lore_db.io import read_json, utc_now


CANONICAL_FILES = {
    "items": "items.jsonl",
    "localizations": "localizations.jsonl",
    "documents": "documents.jsonl",
    "sections": "sections.jsonl",
    "text_units": "text_units.jsonl",
    "relations": "relations.jsonl",
    "entity_names": "entity_names.jsonl",
    "textmap_entries": "textmap_entries.jsonl",
}

SQLITE_TABLES = [
    "items",
    "localizations",
    "documents",
    "sections",
    "text_units",
    "relations",
    "textmap_entries",
]

FTS_TABLES = [
    "text_units_fts_unicode",
    "text_units_fts_trigram",
    "textmap_fts_unicode",
    "textmap_fts_trigram",
]


def audit_project_amber_v2(
    root: Path | str,
    *,
    canonical_root: Path | None = None,
    search_db: Path | None = None,
    scan_jsonl: bool = True,
    max_samples: int = 20,
) -> dict[str, Any]:
    project_root = Path(root).resolve()
    canonical_dir = canonical_root or project_root / "data" / "canonical" / "project_amber_v2"
    db_path = search_db or project_root / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
    build_report_path = canonical_dir / "build_report.json"
    report_counts = {}
    if build_report_path.exists():
        report_counts = (read_json(build_report_path).get("counts") or {})

    jsonl_report = audit_jsonl_files(canonical_dir, report_counts, scan=scan_jsonl, max_samples=max_samples)
    sqlite_report = audit_sqlite_db(db_path, jsonl_report.get("counts") or report_counts, max_samples=max_samples)
    issues = []
    issues.extend(jsonl_report.get("issues") or [])
    issues.extend(sqlite_report.get("issues") or [])

    return {
        "version": "project_amber_v2_audit.v0.1",
        "audited_at": utc_now(),
        "ok": not issues,
        "canonical_root": str(canonical_dir),
        "search_db": str(db_path),
        "build_report": {
            "path": str(build_report_path),
            "exists": build_report_path.exists(),
            "counts": report_counts,
        },
        "jsonl": jsonl_report,
        "sqlite": sqlite_report,
        "issues": issues,
    }


def audit_jsonl_files(
    canonical_root: Path,
    expected_counts: dict[str, Any],
    *,
    scan: bool,
    max_samples: int,
) -> dict[str, Any]:
    counts: dict[str, int] = {}
    parse_errors: dict[str, list[dict[str, Any]]] = {}
    missing_files = []
    count_mismatches = []
    issues = []

    for key, filename in CANONICAL_FILES.items():
        path = canonical_root / filename
        if not path.exists():
            missing_files.append(str(path))
            issues.append({"code": "missing_jsonl_file", "file": str(path), "severity": "error"})
            continue
        if not scan:
            continue
        count, errors = count_jsonl(path, max_samples=max_samples)
        counts[key] = count
        if errors:
            parse_errors[key] = errors
            issues.append({"code": "jsonl_parse_errors", "file": str(path), "count": len(errors), "severity": "error"})

    if scan:
        for key, actual in counts.items():
            expected = expected_counts.get(key)
            if expected is None:
                continue
            if int(expected) != actual:
                mismatch = {"name": key, "expected": int(expected), "actual": actual}
                count_mismatches.append(mismatch)
                issues.append({"code": "jsonl_count_mismatch", **mismatch, "severity": "error"})

    return {
        "scanned": scan,
        "counts": counts,
        "expected_counts": {key: expected_counts.get(key) for key in CANONICAL_FILES},
        "missing_files": missing_files,
        "count_mismatches": count_mismatches,
        "parse_errors": parse_errors,
        "issues": issues,
    }


def audit_sqlite_db(db_path: Path, expected_counts: dict[str, Any], *, max_samples: int) -> dict[str, Any]:
    if not db_path.exists():
        return {
            "exists": False,
            "issues": [{"code": "missing_sqlite_db", "path": str(db_path), "severity": "error"}],
        }

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    issues = []
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        issues.append({"code": "sqlite_integrity_check_failed", "result": integrity, "severity": "error"})

    existing_tables = {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    }
    missing_tables = [table for table in [*SQLITE_TABLES, *FTS_TABLES] if table not in existing_tables]
    for table in missing_tables:
        issues.append({"code": "missing_sqlite_table", "table": table, "severity": "error"})

    table_counts = {}
    count_mismatches = []
    for table in SQLITE_TABLES:
        if table not in existing_tables:
            continue
        actual = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        table_counts[table] = actual
        expected = expected_counts.get(table)
        if expected is not None and int(expected) != actual:
            mismatch = {"name": table, "expected": int(expected), "actual": actual}
            count_mismatches.append(mismatch)
            issues.append({"code": "sqlite_count_mismatch", **mismatch, "severity": "error"})

    fts_counts = {}
    for table in FTS_TABLES:
        if table not in existing_tables:
            continue
        fts_counts[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    reference_checks = audit_sqlite_references(conn, max_samples=max_samples)
    issues.extend(reference_checks.get("issues") or [])
    conn.close()

    return {
        "exists": True,
        "integrity_check": integrity,
        "tables": sorted(existing_tables),
        "missing_tables": missing_tables,
        "table_counts": table_counts,
        "fts_counts": fts_counts,
        "count_mismatches": count_mismatches,
        "references": reference_checks,
        "issues": issues,
    }


def audit_sqlite_references(conn: sqlite3.Connection, *, max_samples: int) -> dict[str, Any]:
    checks = {
        "localizations_without_item": """
            SELECT l.canonical_id
            FROM localizations l
            LEFT JOIN items i ON i.canonical_id = l.canonical_id
            WHERE i.canonical_id IS NULL
        """,
        "non_list_documents_without_item": """
            SELECT d.document_id
            FROM documents d
            LEFT JOIN items i ON i.canonical_id = d.canonical_id
            WHERE d.document_kind != 'list' AND i.canonical_id IS NULL
        """,
        "sections_without_document": """
            SELECT s.section_id
            FROM sections s
            LEFT JOIN documents d ON d.document_id = s.document_id
            WHERE d.document_id IS NULL
        """,
        "text_units_without_document": """
            SELECT u.unit_id
            FROM text_units u
            LEFT JOIN documents d ON d.document_id = u.document_id
            WHERE d.document_id IS NULL
        """,
        "text_units_without_section": """
            SELECT u.unit_id
            FROM text_units u
            LEFT JOIN sections s ON s.section_id = u.section_id
            WHERE u.section_id IS NOT NULL AND s.section_id IS NULL
        """,
        "relations_source_without_item": """
            SELECT r.relation_id
            FROM relations r
            LEFT JOIN items i ON i.canonical_id = r.source_id
            WHERE i.canonical_id IS NULL
        """,
        "relations_target_without_section": """
            SELECT r.relation_id
            FROM relations r
            LEFT JOIN sections s ON s.section_id = r.target_id
            WHERE s.section_id IS NULL
        """,
    }
    results = {}
    issues = []
    for name, sql in checks.items():
        count_sql = f"SELECT COUNT(*) FROM ({sql})"
        count = int(conn.execute(count_sql).fetchone()[0])
        samples = []
        if count:
            sample_sql = f"{sql} LIMIT ?"
            samples = [row[0] for row in conn.execute(sample_sql, (max_samples,)).fetchall()]
            issues.append({"code": "sqlite_reference_issue", "check": name, "count": count, "samples": samples, "severity": "error"})
        results[name] = {"count": count, "samples": samples}
    return {"checks": results, "issues": issues}


def count_jsonl(path: Path, *, max_samples: int) -> tuple[int, list[dict[str, Any]]]:
    count = 0
    errors: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                json.loads(line)
            except json.JSONDecodeError as exc:
                if len(errors) < max_samples:
                    errors.append({"line": line_number, "error": str(exc)})
    return count, errors
