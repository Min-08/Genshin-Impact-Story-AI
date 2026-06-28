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
from amber_project_db_builder.io import load_config, write_json
from amber_project_db_builder.project_amber import _iter_item_ids, _make_raw_record, _raw_path, _unwrap_response


SOURCE = "project_amber"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", nargs="+")
    parser.add_argument("--content-types", nargs="+")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--include-unreleased", action="store_true")
    args = parser.parse_args()

    config = load_config(ROOT)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    policy = config.get("policy", {})
    languages = args.languages or list(lang_config.keys())
    content_types = args.content_types or list(source_config["content_types"])
    list_only = set(source_config.get("list_only_content_types", []))
    base_url = source_config["base_url"].rstrip("/")
    future_release_grace_days = int(policy.get("future_release_grace_days", 7))

    targets: list[dict[str, Any]] = []
    skipped_existing = 0
    for language in languages:
        amber_language = lang_config[language][SOURCE]
        for content_type in content_types:
            if content_type in list_only:
                continue
            list_path = _raw_path(ROOT, language, content_type, "list")
            if not list_path.exists():
                raise FileNotFoundError(f"Missing list file: {list_path}")
            import json

            list_record = json.loads(list_path.read_text(encoding="utf-8"))
            item_ids = _iter_item_ids(
                list_record["payload"],
                include_unreleased=args.include_unreleased,
                future_release_grace_days=future_release_grace_days,
            )
            for item_id in item_ids:
                detail_path = _raw_path(ROOT, language, content_type, "detail", item_id)
                if detail_path.exists() and not args.force:
                    skipped_existing += 1
                    continue
                targets.append(
                    {
                        "language": language,
                        "amber_language": amber_language,
                        "content_type": content_type,
                        "item_id": item_id,
                        "url": f"{base_url}/{amber_language}/{content_type}/{item_id}",
                        "path": detail_path,
                    }
                )

    started = time.time()
    errors: list[dict[str, Any]] = []
    fetched: list[dict[str, Any]] = []
    print(
        {
            "targets": len(targets),
            "skipped_existing": skipped_existing,
            "workers": args.workers,
        },
        flush=True,
    )

    def fetch_one(target: dict[str, Any]) -> dict[str, Any]:
        payload = fetch_json(target["url"], sleep_seconds=0)
        data = _unwrap_response(payload)
        record = _make_raw_record(
            source_url=target["url"],
            language=target["language"],
            content_type=target["content_type"],
            kind="detail",
            payload=data,
            item_id=target["item_id"],
        )
        write_json(target["path"], record.to_dict())
        return {
            "language": target["language"],
            "content_type": target["content_type"],
            "item_id": target["item_id"],
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
        "targets": len(targets),
        "skipped_existing": skipped_existing,
        "fetched": len(fetched),
        "errors": errors,
        "by_content_type": dict(Counter(row["content_type"] for row in fetched)),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_json(ROOT / "data" / "logs" / "project_amber_detail_parallel_last_run.json", report)
    print(report)


if __name__ == "__main__":
    main()
