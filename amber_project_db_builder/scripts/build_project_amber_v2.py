from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amber_project_db_builder.pipeline.project_amber_v2 import build_project_amber_v2


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Project Amber v2 readable/canonical/SQLite outputs.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Package root. Defaults to this directory.")
    args = parser.parse_args()

    report = build_project_amber_v2(args.root)
    sys.stdout.buffer.write((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
