from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.search_engine.aliases import build_entity_aliases
from genshin_lore_db.search_engine.engine import write_search_engine_assets


def main() -> int:
    alias_report = build_entity_aliases(ROOT)
    engine_report = write_search_engine_assets(ROOT)
    sys.stdout.buffer.write(
        (json.dumps({"aliases": alias_report, "engine": engine_report}, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
