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

from amber_project_db_builder import __version__
from amber_project_db_builder.http import fetch_json
from amber_project_db_builder.io import load_config, safe_filename, sha256_json, utc_now, write_json
from amber_project_db_builder.models import RawRecord
from amber_project_db_builder.project_amber import _unwrap_response


SOURCE = "project_amber"
UNDETERMINED_LANGUAGE = "und"

LANGUAGE_ENDPOINTS = [
    "pronoun",
    "everything",
    "manualWeapon",
    "combine",
    "dailyDungeon",
    "upgrade",
    "tower",
]

STATIC_ENDPOINTS = {
    "static_changelog": "api/v2/static/changelog",
    "avatarCurve": "api/v2/static/avatarCurve",
    "weaponCurve": "api/v2/static/weaponCurve",
    "reliquaryCurve": "api/v2/static/reliquaryCurve",
    "monsterCurve": "api/v2/static/monsterCurve",
    "event": "assets/data/event.json",
}

ADVANCED_ENDPOINTS = {
    "advanced_avatar_guide": ("avatar", "api/v2/static/advanced/avatarGuides/{item_id}"),
    "advanced_weapon_guide": ("weapon", "api/v2/static/advanced/weaponGuides/{item_id}"),
    "advanced_reliquary_guide": ("reliquary", "api/v2/static/advanced/reliquaryGuides/{item_id}"),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--languages", nargs="+")
    parser.add_argument("--content-types", nargs="+")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--skip-advanced", action="store_true")
    args = parser.parse_args()

    report = crawl_project_amber_extras(
        ROOT,
        languages=args.languages,
        content_types=args.content_types,
        workers=args.workers,
        force=args.force,
        include_advanced=not args.skip_advanced,
    )
    print(report)


def crawl_project_amber_extras(
    root: Path,
    *,
    languages: list[str] | None = None,
    content_types: list[str] | None = None,
    workers: int = 8,
    force: bool = False,
    include_advanced: bool = True,
) -> dict[str, Any]:
    config = load_config(root)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    if languages is None:
        languages = list(lang_config.keys())
    selected = set(content_types) if content_types else None
    base_url = source_config["base_url"].rstrip("/")
    site_url = base_url.removesuffix("/api/v2")

    targets: list[dict[str, Any]] = []
    skipped_existing = 0

    for language in languages:
        if language not in lang_config:
            raise ValueError(f"Unknown language: {language}")
        amber_language = lang_config[language][SOURCE]
        for endpoint in LANGUAGE_ENDPOINTS:
            if selected is not None and endpoint not in selected:
                continue
            path = _raw_path(root, language, endpoint, "list")
            if path.exists() and not force:
                skipped_existing += 1
                continue
            targets.append(
                {
                    "language": language,
                    "content_type": endpoint,
                    "kind": "list",
                    "item_id": None,
                    "url": f"{base_url}/{amber_language}/{endpoint}",
                    "path": path,
                }
            )

    for content_type, endpoint in STATIC_ENDPOINTS.items():
        if selected is not None and content_type not in selected:
            continue
        path = _raw_path(root, UNDETERMINED_LANGUAGE, content_type, "list")
        if path.exists() and not force:
            skipped_existing += 1
            continue
        targets.append(
            {
                "language": UNDETERMINED_LANGUAGE,
                "content_type": content_type,
                "kind": "list",
                "item_id": None,
                "url": f"{site_url}/{endpoint}",
                "path": path,
            }
        )

    if include_advanced:
        for content_type, (source_content_type, endpoint_template) in ADVANCED_ENDPOINTS.items():
            if selected is not None and content_type not in selected:
                continue
            item_ids = _advanced_item_ids(root, source_content_type)
            for item_id in item_ids:
                path = _raw_path(root, UNDETERMINED_LANGUAGE, content_type, "detail", item_id)
                if path.exists() and not force:
                    skipped_existing += 1
                    continue
                targets.append(
                    {
                        "language": UNDETERMINED_LANGUAGE,
                        "content_type": content_type,
                        "kind": "detail",
                        "item_id": item_id,
                        "url": f"{site_url}/{endpoint_template.format(item_id=item_id)}",
                        "path": path,
                    }
                )

    started = time.time()
    print({"targets": len(targets), "skipped_existing": skipped_existing, "workers": workers}, flush=True)
    fetched: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    def fetch_one(target: dict[str, Any]) -> dict[str, Any]:
        fetched_payload = fetch_json(target["url"], sleep_seconds=0)
        payload = _unwrap_response(fetched_payload)
        record = _make_raw_record(
            source_url=target["url"],
            language=target["language"],
            content_type=target["content_type"],
            kind=target["kind"],
            payload=payload,
            item_id=target["item_id"],
        )
        write_json(target["path"], record.to_dict())
        return {
            "language": target["language"],
            "content_type": target["content_type"],
            "kind": target["kind"],
            "item_id": target["item_id"],
            "path": str(target["path"]),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
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
                        "kind": target["kind"],
                        "item_id": target["item_id"],
                        "error": str(error),
                    }
                )
            if index % 100 == 0 or index == len(targets):
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

    event_details = _crawl_event_details(root, force=force)

    report = {
        "source": SOURCE,
        "targets": len(targets),
        "skipped_existing": skipped_existing,
        "fetched": len(fetched),
        "errors": errors,
        "event_details": event_details,
        "by_content_type": dict(Counter(row["content_type"] for row in fetched)),
        "elapsed_seconds": round(time.time() - started, 1),
    }
    write_json(root / "data" / "logs" / "project_amber_extras_last_run.json", report)
    return report


def _crawl_event_details(root: Path, *, force: bool) -> dict[str, Any]:
    event_list_path = _raw_path(root, UNDETERMINED_LANGUAGE, "event", "list")
    if not event_list_path.exists():
        return {"fetched": 0, "skipped_existing": 0, "errors": [{"error": "missing event list"}]}

    import json

    event_record = json.loads(event_list_path.read_text(encoding="utf-8"))
    payload = event_record.get("payload")
    if not isinstance(payload, dict):
        return {"fetched": 0, "skipped_existing": 0, "errors": [{"error": "event list payload is not a dict"}]}

    fetched = 0
    skipped_existing = 0
    errors: list[dict[str, Any]] = []
    site_url = event_record["source_url"].split("/assets/data/event.json")[0]
    for event_id in sorted(payload.keys(), key=str):
        path = _raw_path(root, UNDETERMINED_LANGUAGE, "event", "detail", str(event_id))
        if path.exists() and not force:
            skipped_existing += 1
            continue
        url = f"{site_url}/assets/data/event/{event_id}.json"
        try:
            data = fetch_json(url, sleep_seconds=0)
            record = _make_raw_record(
                source_url=url,
                language=UNDETERMINED_LANGUAGE,
                content_type="event",
                kind="detail",
                payload=data,
                item_id=str(event_id),
            )
            write_json(path, record.to_dict())
            fetched += 1
        except Exception as error:
            errors.append({"url": url, "item_id": str(event_id), "error": str(error)})
    return {"fetched": fetched, "skipped_existing": skipped_existing, "errors": errors}


def _advanced_item_ids(root: Path, content_type: str) -> list[str]:
    detail_root = root / "data" / "raw" / SOURCE / "en" / content_type / "detail"
    if not detail_root.exists():
        return []
    item_ids: list[str] = []
    for path in sorted(detail_root.glob("*.raw.json")):
        item_id = path.name.removesuffix(".raw.json")
        if _should_skip_advanced_guide(path, content_type):
            continue
        item_ids.append(item_id)
    return item_ids


def _should_skip_advanced_guide(path: Path, content_type: str) -> bool:
    import json

    payload = json.loads(path.read_text(encoding="utf-8")).get("payload")
    if not isinstance(payload, dict):
        return True
    if content_type == "weapon":
        return bool(payload.get("isWeaponSkin"))
    if content_type == "reliquary":
        suit = payload.get("suit")
        return not isinstance(suit, dict) or len(suit) < 5
    return False


def _raw_path(root: Path, language: str, content_type: str, kind: str, item_id: str | None = None) -> Path:
    base = root / "data" / "raw" / SOURCE / language / content_type
    if kind == "list":
        return base / "list.raw.json"
    if item_id is None:
        raise ValueError("item_id is required for detail records")
    return base / "detail" / f"{safe_filename(item_id)}.raw.json"


def _make_raw_record(
    *,
    source_url: str,
    language: str,
    content_type: str,
    kind: str,
    payload: Any,
    item_id: str | None,
) -> RawRecord:
    raw_id_parts = [SOURCE, language, content_type, kind]
    if item_id is not None:
        raw_id_parts.append(str(item_id))
    return RawRecord(
        raw_id=":".join(raw_id_parts),
        source=SOURCE,
        source_url=source_url,
        fetched_at=utc_now(),
        language=language,
        raw_format="json",
        content_hash=sha256_json(payload),
        crawler_version=__version__,
        payload=payload,
        metadata={"content_type": content_type, "kind": kind, "item_id": item_id},
    )


if __name__ == "__main__":
    main()
