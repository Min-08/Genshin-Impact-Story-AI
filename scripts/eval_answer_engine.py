from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.io import write_json
from genshin_lore_db.search_engine.answer_evaluation import evaluate_answer_engine, load_answer_evaluation_set
from genshin_lore_db.search_engine.local_llm import DEFAULT_OLLAMA_MODEL


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate deterministic and local-LLM answer QA behavior.")
    parser.add_argument("--set", dest="set_path", default=str(ROOT / "config" / "answer_evaluation_set.json"))
    parser.add_argument("--out", default=str(ROOT / "data" / "processed" / "search_engine" / "answer_evaluation_report.json"))
    parser.add_argument("--llm", action="store_true", help="Enable local LLM rewrite before final-answer evaluation.")
    parser.add_argument("--model", default=DEFAULT_OLLAMA_MODEL, help="Ollama model name for --llm.")
    parser.add_argument("--fail-under", action="store_true", help="Return non-zero when configured thresholds are not met.")
    args = parser.parse_args()

    evaluation_set = load_answer_evaluation_set(Path(args.set_path))
    report = evaluate_answer_engine(ROOT, evaluation_set, use_llm=args.llm, model=args.model)
    write_json(Path(args.out), report)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))

    if args.fail_under and not all(report.get("passed_thresholds", {}).values()):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
