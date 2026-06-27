from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.io import write_json
from genshin_lore_db.search_engine.engine import LoreSearchEngine
from genshin_lore_db.search_engine.evaluation import evaluate_search_engine, load_evaluation_set


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate the developer search engine against a small retrieval set.")
    parser.add_argument("--set", dest="set_path", default=str(ROOT / "config" / "search_evaluation_set.json"))
    parser.add_argument("--out", default=str(ROOT / "data" / "processed" / "search_engine" / "evaluation_report.json"))
    parser.add_argument("--fail-under", action="store_true", help="Return non-zero when configured thresholds are not met.")
    args = parser.parse_args()

    engine = LoreSearchEngine.open(ROOT)
    evaluation_set = load_evaluation_set(Path(args.set_path))
    report = evaluate_search_engine(engine, evaluation_set)
    write_json(Path(args.out), report)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if args.fail_under and not all(report.get("passed_thresholds", {}).values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
