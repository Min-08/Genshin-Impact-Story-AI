from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amber_project_db_builder.io import write_json
from amber_project_db_builder.pipeline.project_amber_v2_audit import audit_project_amber_v2


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit Project Amber v2 JSONL and SQLite outputs.")
    parser.add_argument("--root", default=str(ROOT), help="Project root. Defaults to this repository.")
    parser.add_argument("--canonical-root", type=Path, help="Override data/canonical/project_amber_v2.")
    parser.add_argument("--search-db", type=Path, help="Override data/processed/search_v2/project_amber_search.sqlite3.")
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "processed" / "search_v2" / "audit_report.json")
    parser.add_argument("--skip-jsonl-scan", action="store_true", help="Skip full JSONL line counting and parse checks.")
    parser.add_argument("--fail-on-issues", action="store_true", help="Return non-zero if any audit issue is found.")
    args = parser.parse_args()

    report = audit_project_amber_v2(
        Path(args.root),
        canonical_root=args.canonical_root,
        search_db=args.search_db,
        scan_jsonl=not args.skip_jsonl_scan,
    )
    write_json(args.out, report)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    if args.fail_on_issues and not report.get("ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
