from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.io import write_json
from genshin_lore_db.pipeline.project_amber_v2_evaluation import (
    evaluate_project_amber_v2_search,
    load_project_amber_v2_evaluation_set,
)
from genshin_lore_db.search_engine.engine import LoreSearchEngine
from genshin_lore_db.search_engine.evaluation import evaluate_search_engine, load_evaluation_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the developer search engine against a small retrieval set.")
    parser.add_argument("--db-version", choices=["v2", "v1"], default="v2")
    parser.add_argument("--db", help="Override the default search DB path")
    parser.add_argument("--set", dest="set_path")
    parser.add_argument("--out")
    parser.add_argument("--fail-under", action="store_true", help="Return non-zero when configured thresholds are not met.")
    args = parser.parse_args()

    if args.db_version == "v2":
        db_path = Path(args.db) if args.db else ROOT / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
        set_path = Path(args.set_path) if args.set_path else ROOT / "config" / "project_amber_v2_search_evaluation_set.json"
        out_path = Path(args.out) if args.out else ROOT / "data" / "processed" / "search_v2" / "evaluation_report.json"
        evaluation_set = load_project_amber_v2_evaluation_set(set_path)
        report = evaluate_project_amber_v2_search(db_path, evaluation_set)
    else:
        db_root = Path(args.db) if args.db else ROOT
        set_path = Path(args.set_path) if args.set_path else ROOT / "config" / "search_evaluation_set.json"
        out_path = Path(args.out) if args.out else ROOT / "data" / "processed" / "search_engine" / "evaluation_report.json"
        engine = LoreSearchEngine.open(db_root)
        evaluation_set = load_evaluation_set(set_path)
        report = evaluate_search_engine(engine, evaluation_set)
    write_json(out_path, report)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if args.fail_under and not all(report.get("passed_thresholds", {}).values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
