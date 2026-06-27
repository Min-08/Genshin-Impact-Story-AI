from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from genshin_lore_db.cli import main


if __name__ == "__main__":
    sys.argv.insert(1, "--root")
    sys.argv.insert(2, str(ROOT))
    sys.argv.insert(3, "crawl-project-amber-deep")
    main()
