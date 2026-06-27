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

from genshin_lore_db import __version__
from genshin_lore_db.http import fetch_json, fetch_url
from genshin_lore_db.io import load_config, safe_filename, sha256_text, utc_now, write_json
from genshin_lore_db.models import RawRecord


SOURCE = "genshin_data_readable"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", nargs="+")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    config = load_config(ROOT)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    languages = args.languages or list(lang_config.keys())

    targets: list[dict[str, Any]] = []
    skipped_existing = 0
    for language in languages:
        repo_language = lang_config[language][SOURCE]
        listing_url = f"{source_config['api_url'].rstrip('/')}/{repo_language}?ref=master"
        listing = fetch_json(listing_url)
        if not isinstance(listing, list):
            raise RuntimeError(f"Unexpected listing payload for {listing_url}")
        for item in listing:
            if not isinstance(item, dict) or item.get("type") != "file":
                continue
            filename = item["name"]
            download_url = item.get("download_url") or f"{source_config['raw_url'].rstrip('/')}/{repo_language}/{filename}"
            path = _raw_path(language, filename)
            if path.exists() and not args.force:
                skipped_existing += 1
                continue
            targets.append(
                {
                    "language": language,
                    "repo_language": repo_language,
                    "filename": filename,
                    "url": download_url,
                    "path": path,
                }
            )

    started = time.time()
    fetched: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    print({"targets": len(targets), "skipped_existing": skipped_existing, "workers": args.workers}, flush=True)

    def fetch_one(target: dict[str, Any]) -> dict[str, Any]:
        result = fetch_url(target["url"], sleep_seconds=0)
        text = result.body.decode("utf-8-sig")
        metadata = _metadata_for_filename(target["filename"])
        record = RawRecord(
            raw_id=f"{SOURCE}:{target['language']}:{target['filename']}",
            source=SOURCE,
            source_url=target["url"],
            fetched_at=utc_now(),
            language=target["language"],
            raw_format="text",
            content_hash=sha256_text(text),
            crawler_version=__version__,
            payload=text,
            metadata={
                **metadata,
                "filename": target["filename"],
                "kind": "readable",
                "repo_language": target["repo_language"],
            },
        )
        write_json(target["path"], record.to_dict())
        return {
            "language": target["language"],
            "filename": target["filename"],
            "readable_type": metadata["readable_type"],
            "path": str(target["path"]),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        future_map = {executor.submit(fetch_one, target): target for target in targets}
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            target = future_map[future]
            try:
                fetched.append(future.result())
            except Exception as error:
                errors.append({"url": target["url"], "filename": target["filename"], "error": str(error)})
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
        "by_readable_type": dict(Counter(row["readable_type"] for row in fetched)),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_json(ROOT / "data" / "logs" / "genshin_data_readable_last_run.json", report)
    print(report)


def _raw_path(language: str, filename: str) -> Path:
    return ROOT / "data" / "raw" / SOURCE / language / f"{safe_filename(filename)}.raw.json"


def _metadata_for_filename(filename: str) -> dict[str, Any]:
    stem = filename.rsplit(".", 1)[0]
    if "_" in stem:
        readable_id, repo_language = stem.rsplit("_", 1)
    else:
        readable_id, repo_language = stem, None
    readable_type = "other"
    for prefix in ["Book", "Weapon", "Relic", "Wings", "Costume"]:
        if readable_id.startswith(prefix):
            readable_type = prefix
            break
    return {
        "readable_id": readable_id,
        "readable_type": readable_type,
        "repo_language": repo_language,
    }


if __name__ == "__main__":
    main()
