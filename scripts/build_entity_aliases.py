from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.search_engine.aliases import build_entity_aliases


def main() -> int:
    sys.stdout.buffer.write((json.dumps(build_entity_aliases(ROOT), ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
