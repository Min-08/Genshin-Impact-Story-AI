from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amber_project_db_builder.io import write_json
from amber_project_db_builder.pipeline.project_amber_v2_evaluation import (
    evaluate_project_amber_v2_search,
    load_project_amber_v2_evaluation_set,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Project Amber v2 text-unit search.")
    parser.add_argument("--set", dest="set_path", default=str(ROOT / "config" / "project_amber_v2_search_evaluation_set.json"))
    parser.add_argument("--db", default=str(ROOT / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"))
    parser.add_argument("--out", default=str(ROOT / "data" / "processed" / "search_v2" / "evaluation_report.json"))
    parser.add_argument("--fail-under", action="store_true", help="Return non-zero when configured thresholds are not met.")
    args = parser.parse_args()

    evaluation_set = load_project_amber_v2_evaluation_set(Path(args.set_path))
    report = evaluate_project_amber_v2_search(Path(args.db), evaluation_set)
    write_json(Path(args.out), report)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if args.fail_under and not all(report.get("passed_thresholds", {}).values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
