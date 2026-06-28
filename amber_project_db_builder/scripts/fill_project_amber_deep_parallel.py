from __future__ import annotations

import argparse
import concurrent.futures
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from amber_project_db_builder.http import fetch_json
from amber_project_db_builder.io import load_config, read_json, write_json
from amber_project_db_builder.project_amber import _unwrap_response
from amber_project_db_builder.project_amber_deep import (
    _deep_raw_path,
    _deep_targets_for_detail,
    _make_deep_record,
)


SOURCE = "project_amber"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", nargs="+")
    parser.add_argument("--content-types", nargs="+")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = load_config(ROOT)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    languages = args.languages or list(lang_config.keys())
    content_types = args.content_types or ["avatar", "weapon", "reliquary", "book", "material", "food"]
    base_url = source_config["base_url"].rstrip("/")

    targets: list[dict[str, Any]] = []
    skipped_existing = 0
    details_scanned = 0
    for language in languages:
        amber_language = lang_config[language][SOURCE]
        for content_type in content_types:
            detail_root = ROOT / "data" / "raw" / SOURCE / language / content_type / "detail"
            if not detail_root.exists():
                continue
            for detail_path in sorted(detail_root.glob("*.raw.json")):
                details_scanned += 1
                detail_record = read_json(detail_path)
                item_id = str(detail_record.get("metadata", {}).get("item_id") or detail_path.stem)
                for target in _deep_targets_for_detail(content_type, item_id, detail_record.get("payload")):
                    raw_path = _deep_raw_path(
                        ROOT,
                        language,
                        content_type,
                        target.item_id,
                        target.deep_kind,
                        target.deep_id,
                    )
                    if raw_path.exists() and not args.force:
                        skipped_existing += 1
                        continue
                    targets.append(
                        {
                            "language": language,
                            "amber_language": amber_language,
                            "content_type": content_type,
                            "item_id": target.item_id,
                            "deep_kind": target.deep_kind,
                            "deep_id": target.deep_id,
                            "metadata": target.metadata,
                            "url": f"{base_url}/{amber_language}/{target.endpoint_suffix}",
                            "path": raw_path,
                        }
                    )

    started = time.time()
    errors: list[dict[str, Any]] = []
    fetched: list[dict[str, Any]] = []
    print(
        {
            "details_scanned": details_scanned,
            "targets": len(targets),
            "skipped_existing": skipped_existing,
            "workers": args.workers,
        },
        flush=True,
    )

    def fetch_one(target: dict[str, Any]) -> dict[str, Any]:
        payload = fetch_json(target["url"], sleep_seconds=0)
        data = _unwrap_response(payload)
        record = _make_deep_record(
            source_url=target["url"],
            language=target["language"],
            content_type=target["content_type"],
            item_id=target["item_id"],
            deep_kind=target["deep_kind"],
            deep_id=target["deep_id"],
            payload=data,
            metadata=target["metadata"],
        )
        write_json(target["path"], record.to_dict())
        return {
            "language": target["language"],
            "content_type": target["content_type"],
            "item_id": target["item_id"],
            "deep_kind": target["deep_kind"],
            "deep_id": target["deep_id"],
            "path": str(target["path"]),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(fetch_one, target): target for target in targets}
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            target = future_map[future]
            try:
                fetched.append(future.result())
            except Exception as error:
                errors.append(
                    {
                        "url": target["url"],
                        "language": target["language"],
                        "content_type": target["content_type"],
                        "item_id": target["item_id"],
                        "deep_kind": target["deep_kind"],
                        "deep_id": target["deep_id"],
                        "error": str(error),
                    }
                )
            if index % 250 == 0 or index == len(targets):
                print(
                    {
                        "done": index,
                        "targets": len(targets),
                        "fetched": len(fetched),
                        "errors": len(errors),
                        "elapsed_seconds": round(time.time() - started, 1),
                    },
                    flush=True,
                )

    report = {
        "source": SOURCE,
        "details_scanned": details_scanned,
        "targets": len(targets),
        "skipped_existing": skipped_existing,
        "fetched": len(fetched),
        "errors": errors,
        "by_deep_kind": dict(Counter(row["deep_kind"] for row in fetched)),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_json(ROOT / "data" / "logs" / "project_amber_deep_parallel_last_run.json", report)
    print(report)


if __name__ == "__main__":
    main()
