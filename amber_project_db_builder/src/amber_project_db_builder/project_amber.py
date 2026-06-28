from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from . import __version__
from .http import fetch_json
from .io import ensure_dir, load_config, safe_filename, sha256_json, utc_now, write_json
from .models import RawRecord


SOURCE = "project_amber"


def _unwrap_response(payload: Any) -> Any:
    if isinstance(payload, dict) and "data" in payload and payload.get("response") == 200:
        return payload["data"]
    return payload


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
    item_id: str | None = None,
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


def _is_marked_unreleased(item: dict[str, Any]) -> bool:
    marker_fields = ["name", "title", "chapterTitle", "route"]
    for field in marker_fields:
        value = item.get(field)
        if isinstance(value, str) and "$UNRELEASED" in value.upper():
            return True
    return False


def _is_future_release(item: dict[str, Any], grace_days: int) -> bool:
    release = item.get("release")
    if not isinstance(release, (int, float)):
        return False
    return release > time.time() + grace_days * 24 * 60 * 60


def _iter_item_ids(list_data: dict[str, Any], *, include_unreleased: bool, future_release_grace_days: int) -> list[str]:
    items = list_data.get("items", {})
    if not isinstance(items, dict):
        return []
    ids: list[str] = []
    for item_id, item in items.items():
        if not isinstance(item, dict):
            continue
        if not include_unreleased and (_is_marked_unreleased(item) or _is_future_release(item, future_release_grace_days)):
            continue
        ids.append(str(item_id))
    return ids


def _count_list_entities(content_type: str, list_data: Any) -> int:
    if not isinstance(list_data, dict):
        return 0
    if content_type == "achievement":
        total = 0
        for group in list_data.values():
            if not isinstance(group, dict):
                continue
            achievements = group.get("achievementList", {})
            if isinstance(achievements, dict):
                total += sum(1 for achievement in achievements.values() if isinstance(achievement, dict))
            elif isinstance(achievements, list):
                total += sum(1 for achievement in achievements if isinstance(achievement, dict))
        return total
    items = list_data.get("items", {})
    return len(items) if isinstance(items, dict) else 0


def crawl_project_amber(
    root: Path,
    *,
    languages: list[str] | None = None,
    content_types: list[str] | None = None,
    limit: int | None = None,
    detail_limit: int | None = None,
    skip_details: bool = False,
    include_unreleased: bool | None = None,
    force: bool = False,
    sleep_seconds: float = 0.25,
) -> dict[str, Any]:
    config = load_config(root)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    policy = config.get("policy", {})
    list_only_content_types = set(source_config.get("list_only_content_types", []))
    if languages is None:
        languages = list(lang_config.keys())
    if content_types is None:
        content_types = list(source_config["content_types"])
    if include_unreleased is None:
        include_unreleased = bool(policy.get("include_unreleased_default", False))
    future_release_grace_days = int(policy.get("future_release_grace_days", 7))

    base_url = source_config["base_url"].rstrip("/")
    report: dict[str, Any] = {"source": SOURCE, "lists": [], "details": [], "errors": []}

    for language in languages:
        if language not in lang_config:
            raise ValueError(f"Unknown language: {language}")
        amber_language = lang_config[language][SOURCE]
        for content_type in content_types:
            list_url = f"{base_url}/{amber_language}/{content_type}"
            list_path = _raw_path(root, language, content_type, "list")
            if list_path.exists() and not force:
                list_record = _load_raw_payload(list_path)
                list_data = list_record["payload"]
            else:
                try:
                    list_payload = fetch_json(list_url, sleep_seconds=sleep_seconds)
                    list_data = _unwrap_response(list_payload)
                    record = _make_raw_record(
                        source_url=list_url,
                        language=language,
                        content_type=content_type,
                        kind="list",
                        payload=list_data,
                    )
                    write_json(list_path, record.to_dict())
                except Exception as error:
                    report["errors"].append({"url": list_url, "error": str(error)})
                    continue
                time.sleep(sleep_seconds)

            item_ids = _iter_item_ids(
                list_data,
                include_unreleased=include_unreleased,
                future_release_grace_days=future_release_grace_days,
            )
            if limit is not None:
                item_ids = item_ids[:limit]
            report["lists"].append(
                {
                    "language": language,
                    "content_type": content_type,
                    "items": len(item_ids),
                    "total_entities": _count_list_entities(content_type, list_data),
                    "path": str(list_path),
                }
            )

            if skip_details or content_type in list_only_content_types:
                continue

            detail_ids = item_ids
            if detail_limit is not None:
                detail_ids = detail_ids[:detail_limit]
            for item_id in detail_ids:
                detail_url = f"{base_url}/{amber_language}/{content_type}/{item_id}"
                detail_path = _raw_path(root, language, content_type, "detail", item_id)
                if detail_path.exists() and not force:
                    report["details"].append(
                        {
                            "language": language,
                            "content_type": content_type,
                            "item_id": item_id,
                            "status": "cached",
                            "path": str(detail_path),
                        }
                    )
                    continue
                try:
                    detail_payload = fetch_json(detail_url, sleep_seconds=sleep_seconds)
                    detail_data = _unwrap_response(detail_payload)
                    record = _make_raw_record(
                        source_url=detail_url,
                        language=language,
                        content_type=content_type,
                        kind="detail",
                        payload=detail_data,
                        item_id=item_id,
                    )
                    write_json(detail_path, record.to_dict())
                    report["details"].append(
                        {
                            "language": language,
                            "content_type": content_type,
                            "item_id": item_id,
                            "status": "fetched",
                            "path": str(detail_path),
                        }
                    )
                except Exception as error:
                    report["errors"].append({"url": detail_url, "error": str(error)})
                time.sleep(sleep_seconds)

    ensure_dir(root / "data" / "logs")
    write_json(root / "data" / "logs" / "project_amber_last_run.json", report)
    return report


def _load_raw_payload(path: Path) -> dict[str, Any]:
    import json

    return json.loads(path.read_text(encoding="utf-8"))
