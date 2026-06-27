from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from . import __version__
from .http import fetch_json
from .io import ensure_dir, load_config, read_json, safe_filename, sha256_json, utc_now, write_json
from .models import RawRecord
from .project_amber import _unwrap_response


SOURCE = "project_amber"

RELIC_SLOT_IDS = {
    "EQUIP_BRACER": 4,
    "EQUIP_NECKLACE": 2,
    "EQUIP_SHOES": 5,
    "EQUIP_RING": 1,
    "EQUIP_DRESS": 3,
}


@dataclass(frozen=True)
class DeepTarget:
    deep_kind: str
    endpoint_suffix: str
    deep_id: str
    item_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


def crawl_project_amber_deep(
    root: Path,
    *,
    languages: list[str] | None = None,
    content_types: list[str] | None = None,
    limit: int | None = None,
    target_limit: int | None = None,
    force: bool = False,
    sleep_seconds: float = 0.25,
) -> dict[str, Any]:
    config = load_config(root)
    lang_config = config["languages"]
    source_config = config["sources"][SOURCE]
    if languages is None:
        languages = list(lang_config.keys())
    if content_types is None:
        content_types = ["avatar", "weapon", "reliquary", "book", "material", "food"]

    base_url = source_config["base_url"].rstrip("/")
    report: dict[str, Any] = {"source": SOURCE, "deep": [], "errors": []}

    for language in languages:
        if language not in lang_config:
            raise ValueError(f"Unknown language: {language}")
        amber_language = lang_config[language][SOURCE]
        for content_type in content_types:
            detail_paths = sorted((root / "data" / "raw" / SOURCE / language / content_type / "detail").glob("*.raw.json"))
            if limit is not None:
                detail_paths = detail_paths[:limit]
            for detail_path in detail_paths:
                detail_record = read_json(detail_path)
                item_id = str(detail_record.get("metadata", {}).get("item_id") or detail_path.stem)
                payload = detail_record.get("payload")
                targets = list(_deep_targets_for_detail(content_type, item_id, payload))
                if target_limit is not None:
                    targets = targets[:target_limit]
                for target in targets:
                    url = f"{base_url}/{amber_language}/{target.endpoint_suffix}"
                    path = _deep_raw_path(root, language, content_type, target.item_id, target.deep_kind, target.deep_id)
                    if path.exists() and not force:
                        report["deep"].append(
                            {
                                "language": language,
                                "content_type": content_type,
                                "item_id": target.item_id,
                                "deep_kind": target.deep_kind,
                                "deep_id": target.deep_id,
                                "status": "cached",
                                "path": str(path),
                            }
                        )
                        continue
                    try:
                        fetched = fetch_json(url, sleep_seconds=sleep_seconds)
                        data = _unwrap_response(fetched)
                        record = _make_deep_record(
                            source_url=url,
                            language=language,
                            content_type=content_type,
                            item_id=target.item_id,
                            deep_kind=target.deep_kind,
                            deep_id=target.deep_id,
                            payload=data,
                            metadata=target.metadata,
                        )
                        write_json(path, record.to_dict())
                        report["deep"].append(
                            {
                                "language": language,
                                "content_type": content_type,
                                "item_id": target.item_id,
                                "deep_kind": target.deep_kind,
                                "deep_id": target.deep_id,
                                "status": "fetched",
                                "path": str(path),
                            }
                        )
                    except Exception as error:
                        report["errors"].append(
                            {
                                "url": url,
                                "language": language,
                                "content_type": content_type,
                                "item_id": target.item_id,
                                "deep_kind": target.deep_kind,
                                "deep_id": target.deep_id,
                                "error": str(error),
                            }
                        )
                    time.sleep(sleep_seconds)

    ensure_dir(root / "data" / "logs")
    write_json(root / "data" / "logs" / "project_amber_deep_last_run.json", report)
    return report


def _deep_targets_for_detail(content_type: str, item_id: str, payload: Any) -> Iterable[DeepTarget]:
    if not isinstance(payload, dict):
        return []
    if content_type == "book":
        return _book_targets(item_id, payload)
    if content_type == "weapon":
        return _readable_story_targets("Weapon", "weapon_story", item_id, payload)
    if content_type == "reliquary":
        return _reliquary_targets(item_id, payload)
    if content_type in {"material", "food"}:
        return _readable_story_targets("Wings", "material_story", item_id, payload)
    if content_type == "avatar":
        return _avatar_targets(item_id, payload)
    return []


def _book_targets(item_id: str, payload: dict[str, Any]) -> list[DeepTarget]:
    targets: list[DeepTarget] = []
    volumes = payload.get("volume", [])
    if not isinstance(volumes, list):
        return targets
    for index, volume in enumerate(volumes):
        if not isinstance(volume, dict):
            continue
        story_id = volume.get("storyId")
        if story_id is None:
            continue
        readable_id = f"Book{story_id}"
        targets.append(
            DeepTarget(
                deep_kind="readable",
                endpoint_suffix=f"readable/{readable_id}",
                deep_id=readable_id,
                item_id=item_id,
                metadata={
                    "readable_type": "Book",
                    "story_id": str(story_id),
                    "volume_index": index,
                    "volume_id": str(volume.get("id")) if volume.get("id") is not None else None,
                    "title": volume.get("name"),
                    "description": volume.get("description"),
                    "parent_title": payload.get("name"),
                },
            )
        )
    return targets


def _readable_story_targets(prefix: str, deep_kind: str, item_id: str, payload: dict[str, Any]) -> list[DeepTarget]:
    story_ids = payload.get("storyId")
    if story_ids is None:
        return []
    if not isinstance(story_ids, list):
        story_ids = [story_ids]
    targets: list[DeepTarget] = []
    for index, story_id in enumerate(story_ids):
        if story_id is None:
            continue
        readable_id = f"{prefix}{story_id}"
        targets.append(
            DeepTarget(
                deep_kind=deep_kind,
                endpoint_suffix=f"readable/{readable_id}",
                deep_id=readable_id,
                item_id=item_id,
                metadata={
                    "readable_type": prefix,
                    "story_id": str(story_id),
                    "story_index": index,
                    "title": payload.get("name"),
                    "description": payload.get("description"),
                },
            )
        )
    return targets


def _reliquary_targets(item_id: str, payload: dict[str, Any]) -> list[DeepTarget]:
    suit = payload.get("suit", {})
    if not isinstance(suit, dict):
        return []
    targets: list[DeepTarget] = []
    for slot, slot_id in RELIC_SLOT_IDS.items():
        item = suit.get(slot)
        if not isinstance(item, dict):
            continue
        readable_id = f"Relic{item_id}_{slot_id}"
        targets.append(
            DeepTarget(
                deep_kind="reliquary_story",
                endpoint_suffix=f"readable/{readable_id}",
                deep_id=readable_id,
                item_id=item_id,
                metadata={
                    "readable_type": "Relic",
                    "slot": slot,
                    "slot_id": slot_id,
                    "title": item.get("name"),
                    "description": item.get("description"),
                    "parent_title": payload.get("name"),
                },
            )
        )
    return targets


def _avatar_targets(item_id: str, payload: dict[str, Any]) -> list[DeepTarget]:
    avatar_fetter_id = item_id.split("-")[0] if "-" in item_id else item_id
    targets = [
        DeepTarget(
            deep_kind="avatar_fetter",
            endpoint_suffix=f"avatarFetter/{avatar_fetter_id}",
            deep_id=str(avatar_fetter_id),
            item_id=item_id,
            metadata={
                "title": payload.get("name"),
                "readable_type": "avatarFetter",
                "avatar_fetter_id": avatar_fetter_id,
            },
        )
    ]
    other = payload.get("other") or {}
    costumes = other.get("costume", []) if isinstance(other, dict) else []
    if isinstance(costumes, list):
        for index, costume in enumerate(costumes):
            if not isinstance(costume, dict):
                continue
            story_id = costume.get("storyId")
            if story_id is None:
                continue
            readable_id = f"Costume{story_id}"
            targets.append(
                DeepTarget(
                    deep_kind="costume_story",
                    endpoint_suffix=f"readable/{readable_id}",
                    deep_id=readable_id,
                    item_id=item_id,
                    metadata={
                        "readable_type": "Costume",
                        "story_id": str(story_id),
                        "costume_index": index,
                        "title": costume.get("name"),
                        "description": costume.get("description"),
                        "parent_title": payload.get("name"),
                    },
                )
            )
    return targets


def _deep_raw_path(root: Path, language: str, content_type: str, item_id: str, deep_kind: str, deep_id: str) -> Path:
    return (
        root
        / "data"
        / "raw"
        / SOURCE
        / language
        / content_type
        / "deep"
        / safe_filename(item_id)
        / f"{safe_filename(deep_kind)}-{safe_filename(deep_id)}.raw.json"
    )


def _make_deep_record(
    *,
    source_url: str,
    language: str,
    content_type: str,
    item_id: str,
    deep_kind: str,
    deep_id: str,
    payload: Any,
    metadata: dict[str, Any],
) -> RawRecord:
    raw_id = f"{SOURCE}:{language}:{content_type}:deep:{item_id}:{deep_kind}:{deep_id}"
    return RawRecord(
        raw_id=raw_id,
        source=SOURCE,
        source_url=source_url,
        fetched_at=utc_now(),
        language=language,
        raw_format="json",
        content_hash=sha256_json(payload),
        crawler_version=__version__,
        payload=payload,
        metadata={
            **metadata,
            "content_type": content_type,
            "kind": "deep",
            "deep_kind": deep_kind,
            "deep_id": deep_id,
            "item_id": item_id,
        },
    )
