from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable

from .io import read_json, sha256_text, stable_json_dumps, write_json, write_jsonl
from .models import ChunkRecord, DocumentRecord, EntityNameRecord


PROJECT_AMBER = "project_amber"
DIMBREATH_TEXTMAP = "dimbreath_textmap"
GENSHIN_DATA_READABLE = "genshin_data_readable"
OFFICIAL_TEXT = "official_text"

TITLE_FIELDS = ["name", "title", "chapterTitle"]
TEXT_FIELD_HINTS = {
    "name",
    "title",
    "chapterTitle",
    "chapterNum",
    "chapterImageTitle",
    "description",
    "detail",
    "text",
    "role",
    "native",
    "constellation",
}
SKIP_FIELD_HINTS = {
    "icon",
    "route",
    "source_url",
    "content_hash",
    "raw_id",
    "fetched_at",
    "crawler_version",
    "raw_format",
    "metadata",
    "params",
    "costItems",
    "addProps",
    "advancedProps",
    "upgrade",
    "ascension",
}
ENTITY_CONTENT_TYPES = {
    "avatar": "character",
    "weapon": "weapon",
    "gcg": "tcg",
    "reliquary": "artifact",
    "book": "book",
    "material": "material",
    "food": "food",
    "furniture": "furniture",
    "furnitureSuite": "furniture_set",
    "monster": "monster",
    "namecard": "namecard",
    "achievement": "achievement",
}

GENERIC_LIST_CONTENT_TYPES = {
    "pronoun",
    "everything",
    "manualWeapon",
    "combine",
    "dailyDungeon",
    "upgrade",
    "tower",
    "static_changelog",
    "avatarCurve",
    "weaponCurve",
    "reliquaryCurve",
    "monsterCurve",
    "event",
}

GENERIC_DETAIL_CONTENT_TYPES = {
    "event",
    "advanced_avatar_guide",
    "advanced_weapon_guide",
    "advanced_reliquary_guide",
}


def build_canonical(root: Path) -> dict[str, Any]:
    raw_root = root / "data" / "raw" / PROJECT_AMBER
    out_root = root / "data" / "canonical"
    documents: list[DocumentRecord] = []
    entity_names: list[EntityNameRecord] = []
    source_links: list[dict[str, Any]] = []
    textmap_entries: list[dict[str, Any]] = []

    if raw_root.exists():
        for raw_path in sorted(raw_root.glob("*/*/*.raw.json")):
            record = read_json(raw_path)
            if record.get("metadata", {}).get("kind") != "list":
                continue
            language = record["language"]
            content_type = record["metadata"]["content_type"]
            payload = record["payload"]
            if content_type == "achievement" and isinstance(payload, dict):
                entity_names.extend(_achievement_entity_names(language, payload, raw_path))
                continue
            if content_type == "elements" and isinstance(payload, dict):
                entity_names.extend(_elements_entity_names(language, payload, raw_path))
                continue
            items = payload.get("items", {}) if isinstance(payload, dict) else {}
            if isinstance(items, dict):
                entity_names.extend(_entity_names_from_list(content_type, language, items, raw_path))

        for raw_path in sorted(raw_root.glob("*/*/detail/*.raw.json")):
            record = read_json(raw_path)
            doc = _document_from_project_amber_detail(record, raw_path)
            if doc is None:
                continue
            documents.append(doc)
            source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})

        for raw_path in sorted(raw_root.glob("*/*/deep/**/*.raw.json")):
            record = read_json(raw_path)
            for doc in _documents_from_project_amber_deep(record, raw_path):
                documents.append(doc)
                source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})

        # Keep list records as fallback documents when no detail records were fetched.
        detail_doc_keys = {(doc.language, doc.content_type, str(doc.metadata.get("item_id"))) for doc in documents}
        for raw_path in sorted(raw_root.glob("*/*/*.raw.json")):
            record = read_json(raw_path)
            if record.get("metadata", {}).get("kind") != "list":
                continue
            language = record["language"]
            content_type = record["metadata"]["content_type"]
            payload = record["payload"]
            if content_type == "achievement" and isinstance(payload, dict):
                for doc in _achievement_documents_from_list(record, raw_path):
                    documents.append(doc)
                    source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})
                continue
            if content_type == "elements" and isinstance(payload, dict):
                for doc in _element_documents_from_list(record, raw_path):
                    documents.append(doc)
                    source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})
                continue
            if content_type in GENERIC_LIST_CONTENT_TYPES:
                for doc in _generic_documents_from_list(record, raw_path):
                    documents.append(doc)
                    source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})
                continue
            items = payload.get("items", {}) if isinstance(payload, dict) else {}
            for item_id, item in sorted(items.items(), key=lambda pair: str(pair[0])):
                key = (language, content_type, str(item_id))
                if key in detail_doc_keys:
                    continue
                doc = _document_from_project_amber_list_item(record, raw_path, str(item_id), item)
                if doc is None:
                    continue
                documents.append(doc)
                source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})

    textmap_root = root / "data" / "raw" / DIMBREATH_TEXTMAP
    if textmap_root.exists():
        textmap_entries.extend(_textmap_entries(textmap_root))

    genshin_data_root = root / "data" / "raw" / GENSHIN_DATA_READABLE
    if genshin_data_root.exists():
        for raw_path in sorted(genshin_data_root.glob("*/*.raw.json")):
            record = read_json(raw_path)
            doc = _document_from_genshin_data_readable(record, raw_path)
            if doc is None:
                continue
            documents.append(doc)
            source_links.append({"doc_id": doc.doc_id, "raw_ref": str(raw_path), "source_url": doc.source_url})

    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    report = {
        "documents": len(documents),
        "chunks": len(chunks),
        "entity_names": len(entity_names),
        "source_links": len(source_links),
        "textmap_entries": len(textmap_entries),
    }

    write_jsonl(out_root / "documents.jsonl", (doc.to_dict() for doc in documents))
    write_jsonl(out_root / "chunks.jsonl", (chunk.to_dict() for chunk in chunks))
    write_jsonl(out_root / "entity_names.jsonl", (name.to_dict() for name in entity_names))
    write_jsonl(out_root / "source_links.jsonl", source_links)
    write_jsonl(out_root / "textmap_entries.jsonl", textmap_entries)
    write_json(out_root / "build_report.json", report)
    return report


def _textmap_entries(textmap_root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw_path in sorted(textmap_root.glob("*/*.raw.json")):
        record = read_json(raw_path)
        language = record["language"]
        payload = record.get("payload", {})
        if not isinstance(payload, dict):
            continue
        for textmap_id, text in payload.items():
            if not isinstance(text, str):
                continue
            text = clean_text(text)
            if not text:
                continue
            rows.append(
                {
                    "textmap_id": str(textmap_id),
                    "language": language,
                    "text": text,
                    "source": DIMBREATH_TEXTMAP,
                    "source_url": record["source_url"],
                    "raw_ref": str(raw_path),
                    "content_hash": sha256_text(text),
                }
            )
    return rows


def _document_from_genshin_data_readable(record: dict[str, Any], raw_path: Path) -> DocumentRecord | None:
    metadata = record.get("metadata", {})
    payload = record.get("payload")
    if not isinstance(payload, str):
        return None
    text = clean_text(payload)
    if not text:
        return None
    readable_id = str(metadata.get("readable_id") or metadata.get("filename") or raw_path.stem)
    readable_type = str(metadata.get("readable_type") or "other")
    content_type = _content_type_for_readable(readable_type)
    language = record["language"]
    title = readable_id
    return DocumentRecord(
        doc_id=f"{GENSHIN_DATA_READABLE}:{readable_id}:{language}",
        canonical_group_id=f"{GENSHIN_DATA_READABLE}:{readable_id}",
        source=GENSHIN_DATA_READABLE,
        source_url=record["source_url"],
        language=language,
        content_type=content_type,
        officialness=OFFICIAL_TEXT,
        title=title,
        text=text,
        raw_refs=[str(raw_path)],
        metadata={
            "kind": "readable",
            "readable_id": readable_id,
            "readable_type": readable_type,
            "filename": metadata.get("filename"),
        },
    )


def _content_type_for_readable(readable_type: str) -> str:
    return {
        "Book": "book",
        "Weapon": "weapon",
        "Relic": "reliquary",
        "Wings": "material",
        "Costume": "avatar",
    }.get(readable_type, "readable")


def _entity_names_from_list(
    content_type: str,
    language: str,
    items: dict[str, Any],
    raw_path: Path,
) -> Iterable[EntityNameRecord]:
    entity_type = ENTITY_CONTENT_TYPES.get(content_type)
    if entity_type is None:
        return []
    rows: list[EntityNameRecord] = []
    for item_id, item in sorted(items.items(), key=lambda pair: str(pair[0])):
        if not isinstance(item, dict):
            continue
        name = _first_text_field(item, TITLE_FIELDS)
        if not name:
            continue
        canonical_id = f"{PROJECT_AMBER}:{content_type}:{item_id}"
        rows.append(
            EntityNameRecord(
                canonical_id=canonical_id,
                entity_type=entity_type,
                language=language,
                name=clean_text(name),
                source=PROJECT_AMBER,
                source_doc_id=None,
                metadata={"item_id": str(item_id), "raw_ref": str(raw_path), "route": item.get("route")},
            )
        )
    return rows


def _achievement_entity_names(
    language: str,
    groups: dict[str, Any],
    raw_path: Path,
) -> Iterable[EntityNameRecord]:
    rows: list[EntityNameRecord] = []
    for group_id, group in sorted(groups.items(), key=lambda pair: str(pair[0])):
        if not isinstance(group, dict):
            continue
        group_name = _title_for_payload(group)
        if group_name:
            rows.append(
                EntityNameRecord(
                    canonical_id=f"{PROJECT_AMBER}:achievement_group:{group_id}",
                    entity_type="achievement_group",
                    language=language,
                    name=group_name,
                    source=PROJECT_AMBER,
                    source_doc_id=None,
                    metadata={"group_id": str(group_id), "raw_ref": str(raw_path)},
                )
            )
        for achievement_key, achievement in _achievement_items(group):
            for detail in _achievement_details(achievement):
                title = _title_for_payload(detail) or _title_for_payload(achievement)
                if not title:
                    continue
                achievement_id = _achievement_id(detail, achievement, achievement_key)
                rows.append(
                    EntityNameRecord(
                        canonical_id=f"{PROJECT_AMBER}:achievement:{achievement_id}",
                        entity_type="achievement",
                        language=language,
                        name=title,
                        source=PROJECT_AMBER,
                        source_doc_id=None,
                        metadata={
                            "item_id": achievement_id,
                            "group_id": str(group_id),
                            "raw_ref": str(raw_path),
                            "version": achievement.get("version"),
                        },
                    )
                )
    return rows


def _elements_entity_names(
    language: str,
    payload: dict[str, Any],
    raw_path: Path,
) -> Iterable[EntityNameRecord]:
    rows: list[EntityNameRecord] = []
    for section, entity_type in [("resonance", "element_resonance"), ("tutorials", "element_tutorial")]:
        section_items = payload.get(section, {})
        if not isinstance(section_items, dict):
            continue
        for item_id, item in sorted(section_items.items(), key=lambda pair: str(pair[0])):
            if not isinstance(item, dict):
                continue
            name = _first_text_field(item, TITLE_FIELDS)
            if not name:
                continue
            rows.append(
                EntityNameRecord(
                    canonical_id=f"{PROJECT_AMBER}:elements:{section}:{item_id}",
                    entity_type=entity_type,
                    language=language,
                    name=clean_text(name),
                    source=PROJECT_AMBER,
                    source_doc_id=None,
                    metadata={"item_id": str(item_id), "section": section, "raw_ref": str(raw_path)},
                )
            )
    return rows


def _achievement_documents_from_list(record: dict[str, Any], raw_path: Path) -> list[DocumentRecord]:
    language = record["language"]
    groups = record["payload"]
    if not isinstance(groups, dict):
        return []
    docs: list[DocumentRecord] = []
    for group_id, group in sorted(groups.items(), key=lambda pair: str(pair[0])):
        if not isinstance(group, dict):
            continue
        group_name = _title_for_payload(group)
        for achievement_key, achievement in _achievement_items(group):
            for detail in _achievement_details(achievement):
                achievement_id = _achievement_id(detail, achievement, achievement_key)
                title = _title_for_payload(detail) or _title_for_payload(achievement)
                text = _achievement_text(group_name, achievement, detail)
                if not text:
                    continue
                docs.append(
                    DocumentRecord(
                        doc_id=f"{PROJECT_AMBER}:achievement:{achievement_id}:{language}:list",
                        canonical_group_id=f"{PROJECT_AMBER}:achievement:{achievement_id}",
                        source=PROJECT_AMBER,
                        source_url=record["source_url"],
                        language=language,
                        content_type="achievement",
                        officialness=OFFICIAL_TEXT,
                        title=title,
                        text=text,
                        raw_refs=[str(raw_path)],
                        metadata={
                            "item_id": achievement_id,
                            "group_id": str(group_id),
                            "kind": "list",
                            "version": achievement.get("version"),
                            "achievement_key": str(achievement_key),
                        },
                    )
                )
    return docs


def _element_documents_from_list(record: dict[str, Any], raw_path: Path) -> list[DocumentRecord]:
    language = record["language"]
    payload = record["payload"]
    if not isinstance(payload, dict):
        return []
    docs: list[DocumentRecord] = []

    info = payload.get("info", {})
    if isinstance(info, dict):
        text = extract_text(info, content_type="elements")
        title = None
        resonance_info = info.get("resonance")
        if isinstance(resonance_info, dict):
            title = _title_for_payload(resonance_info)
        if text:
            docs.append(
                DocumentRecord(
                    doc_id=f"{PROJECT_AMBER}:elements:info:{language}:list",
                    canonical_group_id=f"{PROJECT_AMBER}:elements:info",
                    source=PROJECT_AMBER,
                    source_url=record["source_url"],
                    language=language,
                    content_type="elements",
                    officialness=OFFICIAL_TEXT,
                    title=title,
                    text=text,
                    raw_refs=[str(raw_path)],
                    metadata={"item_id": "info", "kind": "list", "section": "info"},
                )
            )

    for section in ["resonance", "tutorials", "tips"]:
        section_items = payload.get(section, {})
        if not isinstance(section_items, dict):
            continue
        for item_id, item in sorted(section_items.items(), key=lambda pair: str(pair[0])):
            if not isinstance(item, dict):
                continue
            title = _title_for_payload(item)
            text = extract_text(item, content_type="elements")
            if not text:
                continue
            docs.append(
                DocumentRecord(
                    doc_id=f"{PROJECT_AMBER}:elements:{section}:{item_id}:{language}:list",
                    canonical_group_id=f"{PROJECT_AMBER}:elements:{section}:{item_id}",
                    source=PROJECT_AMBER,
                    source_url=record["source_url"],
                    language=language,
                    content_type="elements",
                    officialness=OFFICIAL_TEXT,
                    title=title,
                    text=text,
                    raw_refs=[str(raw_path)],
                    metadata={"item_id": str(item_id), "kind": "list", "section": section},
                )
            )
    return docs


def _generic_documents_from_list(record: dict[str, Any], raw_path: Path) -> list[DocumentRecord]:
    language = record["language"]
    content_type = record["metadata"]["content_type"]
    payload = record["payload"]
    docs: list[DocumentRecord] = []

    if isinstance(payload, list):
        for index, item in enumerate(payload):
            item_id = _generic_item_id(item, index)
            doc = _generic_document(record, raw_path, item_id, item, section=None)
            if doc is not None:
                docs.append(doc)
        return docs

    if not isinstance(payload, dict):
        doc = _generic_document(record, raw_path, "list", payload, section=None)
        return [doc] if doc is not None else []

    if _is_scalar_map(payload):
        doc = _generic_document(record, raw_path, "list", payload, section=None)
        return [doc] if doc is not None else []

    for key, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
        doc = _generic_document(record, raw_path, str(key), item, section=str(key))
        if doc is not None:
            docs.append(doc)
    return docs


def _generic_document(
    record: dict[str, Any],
    raw_path: Path,
    item_id: str,
    payload: Any,
    *,
    section: str | None,
) -> DocumentRecord | None:
    language = record["language"]
    content_type = record["metadata"]["content_type"]
    title = _title_for_payload(payload) if isinstance(payload, dict) else None
    text = _generic_payload_text(payload, root_label=item_id)
    if not text:
        return None
    safe_item_id = safe_doc_part(item_id)
    return DocumentRecord(
        doc_id=f"{PROJECT_AMBER}:{content_type}:{safe_item_id}:{language}:list",
        canonical_group_id=f"{PROJECT_AMBER}:{content_type}:{safe_item_id}",
        source=PROJECT_AMBER,
        source_url=record["source_url"],
        language=language,
        content_type=content_type,
        officialness=OFFICIAL_TEXT,
        title=title or item_id,
        text=text,
        raw_refs=[str(raw_path)],
        metadata={"item_id": item_id, "kind": "list", "section": section},
    )


def _generic_item_id(item: Any, index: int) -> str:
    if isinstance(item, dict):
        item_id = item.get("id")
        item_type = item.get("type")
        if item_id is not None and item_type is not None:
            return f"{item_type}:{item_id}"
        if item_id is not None:
            return str(item_id)
    return str(index)


def _is_scalar_map(payload: dict[str, Any]) -> bool:
    return all(not isinstance(value, (dict, list)) for value in payload.values())


def _documents_from_project_amber_deep(record: dict[str, Any], raw_path: Path) -> list[DocumentRecord]:
    metadata = record.get("metadata", {})
    if metadata.get("kind") != "deep":
        return []
    deep_kind = metadata.get("deep_kind")
    if deep_kind == "avatar_fetter":
        return _avatar_fetter_documents(record, raw_path)
    doc = _readable_document_from_deep(record, raw_path)
    return [doc] if doc is not None else []


def _readable_document_from_deep(record: dict[str, Any], raw_path: Path) -> DocumentRecord | None:
    metadata = record.get("metadata", {})
    payload = record.get("payload")
    if not isinstance(payload, str):
        return None
    text = _deep_text(metadata, payload)
    if not text:
        return None
    content_type = metadata.get("content_type") or record.get("metadata", {}).get("content_type")
    item_id = str(metadata.get("item_id"))
    deep_id = str(metadata.get("deep_id"))
    deep_kind = str(metadata.get("deep_kind"))
    language = record["language"]
    return DocumentRecord(
        doc_id=f"{PROJECT_AMBER}:{content_type}:{item_id}:{language}:deep:{deep_kind}:{deep_id}",
        canonical_group_id=f"{PROJECT_AMBER}:{content_type}:{item_id}",
        source=PROJECT_AMBER,
        source_url=record["source_url"],
        language=language,
        content_type=content_type,
        officialness=OFFICIAL_TEXT,
        title=clean_text(str(metadata.get("title"))) if metadata.get("title") else None,
        text=text,
        raw_refs=[str(raw_path)],
        metadata={
            "item_id": item_id,
            "kind": "deep",
            "deep_kind": deep_kind,
            "deep_id": deep_id,
            "story_id": metadata.get("story_id"),
            "readable_type": metadata.get("readable_type"),
            "volume_index": metadata.get("volume_index"),
            "slot": metadata.get("slot"),
        },
    )


def _deep_text(metadata: dict[str, Any], payload: str) -> str:
    lines: list[str] = []
    parent_title = metadata.get("parent_title")
    title = metadata.get("title")
    description = metadata.get("description")
    if parent_title:
        lines.append(f"parentTitle: {parent_title}")
    if title:
        lines.append(f"title: {title}")
    if description:
        lines.append(f"description: {description}")
    lines.append(payload)
    return "\n".join(_dedupe_keep_order(clean_text(line) for line in lines if line))


def _avatar_fetter_documents(record: dict[str, Any], raw_path: Path) -> list[DocumentRecord]:
    metadata = record.get("metadata", {})
    payload = record.get("payload")
    if not isinstance(payload, dict):
        return []
    language = record["language"]
    item_id = str(metadata.get("item_id"))
    parent_title = metadata.get("title")
    docs: list[DocumentRecord] = []
    for section in ["story", "quotes"]:
        rows = payload.get(section, {})
        if not isinstance(rows, dict):
            continue
        text = _avatar_fetter_text(rows)
        if not text:
            continue
        section_title = f"{parent_title} {section}" if parent_title else section
        docs.append(
            DocumentRecord(
                doc_id=f"{PROJECT_AMBER}:avatar:{item_id}:{language}:deep:avatar_fetter:{section}",
                canonical_group_id=f"{PROJECT_AMBER}:avatar:{item_id}",
                source=PROJECT_AMBER,
                source_url=record["source_url"],
                language=language,
                content_type="avatar",
                officialness=OFFICIAL_TEXT,
                title=section_title,
                text=text,
                raw_refs=[str(raw_path)],
                metadata={
                    "item_id": item_id,
                    "kind": "deep",
                    "deep_kind": "avatar_fetter",
                    "section": section,
                },
            )
        )
    return docs


def _avatar_fetter_text(rows: dict[str, Any]) -> str:
    lines: list[str] = []
    for _, row in sorted(rows.items(), key=lambda pair: str(pair[0])):
        if not isinstance(row, dict):
            continue
        title = row.get("title")
        title2 = row.get("title2")
        tips = row.get("tips")
        text = row.get("text")
        text2 = row.get("text2")
        if title:
            lines.append(f"title: {title}")
        if tips:
            lines.append(f"tips: {tips}")
        if text:
            lines.append(str(text))
        if title2:
            lines.append(f"title: {title2}")
        if text2:
            lines.append(str(text2))
    return "\n".join(_dedupe_keep_order(clean_text(line) for line in lines if line))


def _achievement_items(group: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    achievements = group.get("achievementList", {})
    if isinstance(achievements, dict):
        return [
            (str(achievement_key), achievement)
            for achievement_key, achievement in sorted(achievements.items(), key=lambda pair: str(pair[0]))
            if isinstance(achievement, dict)
        ]
    if isinstance(achievements, list):
        return [
            (str(index), achievement)
            for index, achievement in enumerate(achievements)
            if isinstance(achievement, dict)
        ]
    return []


def _achievement_details(achievement: dict[str, Any]) -> list[dict[str, Any]]:
    details = achievement.get("details", [])
    if isinstance(details, list):
        rows = [detail for detail in details if isinstance(detail, dict)]
        if rows:
            return rows
    return [achievement]


def _achievement_id(detail: dict[str, Any], achievement: dict[str, Any], fallback: str) -> str:
    detail_id = detail.get("id")
    if detail_id is not None:
        return str(detail_id)
    achievement_id = achievement.get("id")
    if achievement_id is not None:
        return str(achievement_id)
    return str(fallback)


def _achievement_text(group_name: str | None, achievement: dict[str, Any], detail: dict[str, Any]) -> str:
    lines: list[str] = []
    if group_name:
        lines.append(f"achievementGroup: {group_name}")
    version = achievement.get("version")
    if version:
        lines.append(f"version: {version}")
    detail_text = extract_text(detail, content_type="achievement")
    if detail_text:
        lines.append(detail_text)
    tasks_text = extract_text(achievement.get("tasks"), content_type="achievement")
    if tasks_text:
        lines.append(f"tasks:\n{tasks_text}")
    return "\n".join(_dedupe_keep_order(lines))


def _document_from_project_amber_detail(record: dict[str, Any], raw_path: Path) -> DocumentRecord | None:
    metadata = record.get("metadata", {})
    content_type = metadata.get("content_type")
    item_id = str(metadata.get("item_id"))
    language = record["language"]
    payload = record["payload"]
    if not isinstance(payload, dict):
        return None
    title = _title_for_payload(payload)
    text = extract_text(payload, content_type=content_type)
    if not text and content_type in GENERIC_DETAIL_CONTENT_TYPES:
        text = _generic_payload_text(payload, root_label=item_id)
    if not text:
        return None
    return DocumentRecord(
        doc_id=f"{PROJECT_AMBER}:{content_type}:{item_id}:{language}:detail",
        canonical_group_id=f"{PROJECT_AMBER}:{content_type}:{item_id}",
        source=PROJECT_AMBER,
        source_url=record["source_url"],
        language=language,
        content_type=content_type,
        officialness=OFFICIAL_TEXT,
        title=title,
        text=text,
        raw_refs=[str(raw_path)],
        metadata={"item_id": item_id, "kind": "detail", **_detail_metadata(content_type, payload)},
    )


def _document_from_project_amber_list_item(
    record: dict[str, Any],
    raw_path: Path,
    item_id: str,
    item: Any,
) -> DocumentRecord | None:
    if not isinstance(item, dict):
        return None
    content_type = record["metadata"]["content_type"]
    language = record["language"]
    title = _title_for_payload(item)
    text = extract_text(item, content_type=content_type)
    if not text:
        return None
    return DocumentRecord(
        doc_id=f"{PROJECT_AMBER}:{content_type}:{item_id}:{language}:list",
        canonical_group_id=f"{PROJECT_AMBER}:{content_type}:{item_id}",
        source=PROJECT_AMBER,
        source_url=record["source_url"],
        language=language,
        content_type=content_type,
        officialness=OFFICIAL_TEXT,
        title=title,
        text=text,
        raw_refs=[str(raw_path)],
        metadata={"item_id": item_id, "kind": "list", **_detail_metadata(content_type, item)},
    )


def _detail_metadata(content_type: str | None, payload: dict[str, Any]) -> dict[str, Any]:
    if content_type != "quest":
        return {}
    info = payload.get("info") if isinstance(payload.get("info"), dict) else payload
    if not isinstance(info, dict):
        return {}
    return {
        "quest_type": info.get("type"),
        "quest_chapter_num": info.get("chapterNum"),
        "quest_chapter_title": info.get("chapterTitle"),
        "route": info.get("route"),
    }


def _title_for_payload(payload: dict[str, Any]) -> str | None:
    direct = _first_text_field(payload, TITLE_FIELDS)
    if direct:
        return clean_text(direct)
    multilingual = _first_multilingual_text(payload, [*TITLE_FIELDS, "nameFull"])
    if multilingual:
        return clean_text(multilingual)
    info = payload.get("info")
    if isinstance(info, dict):
        nested = _first_text_field(info, TITLE_FIELDS)
        if nested:
            return clean_text(nested)
        nested_multilingual = _first_multilingual_text(info, [*TITLE_FIELDS, "nameFull"])
        if nested_multilingual:
            return clean_text(nested_multilingual)
    return None


def _first_text_field(payload: dict[str, Any], fields: Iterable[str]) -> str | None:
    for field in fields:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _first_multilingual_text(payload: dict[str, Any], fields: Iterable[str]) -> str | None:
    preferred_languages = ["KR", "ko", "EN", "en", "JP", "ja", "CHS", "zh-Hans"]
    for field in fields:
        value = payload.get(field)
        if not isinstance(value, dict):
            continue
        for language in preferred_languages:
            text = value.get(language)
            if isinstance(text, str) and text.strip():
                return text
        for text in value.values():
            if isinstance(text, str) and text.strip():
                return text
    return None


def extract_text(payload: Any, *, content_type: str | None) -> str:
    lines: list[str] = []
    if content_type == "quest":
        lines.extend(_extract_quest_lines(payload))
    lines.extend(_extract_generic_lines(payload))
    deduped = _dedupe_keep_order(clean_text(line) for line in lines)
    return "\n".join(line for line in deduped if line)


def _generic_payload_text(payload: Any, *, root_label: str) -> str:
    lines: list[str] = []

    def walk(value: Any, path: list[str]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, [*path, str(key)])
            return
        if isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, [*path, str(index)])
            return
        if value is None:
            return
        if isinstance(value, str):
            text = clean_text(value)
            if not text:
                return
        elif isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        label = ".".join(path) if path else root_label
        lines.append(f"{label}: {text}")

    walk(payload, [root_label])
    return "\n".join(_dedupe_keep_order(lines))


def _extract_quest_lines(payload: Any) -> list[str]:
    lines: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            role = value.get("role")
            text = value.get("text")
            if isinstance(role, str) and isinstance(text, str):
                lines.append(f"{role}: {text}")
            if isinstance(role, str) and isinstance(text, list):
                for choice in text:
                    if isinstance(choice, dict) and isinstance(choice.get("text"), str):
                        lines.append(f"{role}: {choice['text']}")
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(payload)
    return lines


def _extract_generic_lines(payload: Any, parent_key: str | None = None) -> list[str]:
    lines: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            if key_text in SKIP_FIELD_HINTS:
                continue
            if isinstance(value, str):
                if _should_keep_string(key_text, value):
                    label = _friendly_label(key_text)
                    lines.append(f"{label}: {value}" if label else value)
            else:
                lines.extend(_extract_generic_lines(value, key_text))
    elif isinstance(payload, list):
        for value in payload:
            lines.extend(_extract_generic_lines(value, parent_key))
    return lines


def _should_keep_string(key: str, value: str) -> bool:
    stripped = value.strip()
    if len(stripped) < 2:
        return False
    if key in TEXT_FIELD_HINTS:
        return True
    if any(hint in key.lower() for hint in ["name", "title", "desc", "story", "text", "role"]):
        return True
    if re.search(r"[\u3131-\uD79D\u3040-\u30FF\u3400-\u9FFF]", stripped):
        return True
    if len(stripped.split()) >= 4:
        return True
    return False


def _friendly_label(key: str) -> str | None:
    if key in {"text", "description", "detail"}:
        return None
    return key


def clean_text(value: str) -> str:
    value = str(value)
    value = re.sub(r"<color=#[0-9A-Fa-f]+>", "", value)
    value = value.replace("</color>", "")
    value = value.replace("<i>", "").replace("</i>", "")
    value = value.replace("\\n", "\n")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return value.strip()


def _dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if not normalized:
            continue
        fingerprint = sha256_text(normalized)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        result.append(normalized)
    return result


def safe_doc_part(value: str) -> str:
    value = re.sub(r"[^\w.\-:]+", "_", str(value), flags=re.UNICODE)
    return value.strip("._") or "unknown"


def chunk_document(doc: DocumentRecord, *, max_chars: int = 1600) -> list[ChunkRecord]:
    paragraphs = [paragraph.strip() for paragraph in doc.text.split("\n") if paragraph.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for paragraph in paragraphs:
        if current and current_len + len(paragraph) + 1 > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_len = 0
        if len(paragraph) > max_chars:
            if current:
                chunks.append("\n".join(current))
                current = []
                current_len = 0
            chunks.extend(_split_long_text(paragraph, max_chars))
            continue
        current.append(paragraph)
        current_len += len(paragraph) + 1
    if current:
        chunks.append("\n".join(current))

    result: list[ChunkRecord] = []
    for ordinal, text in enumerate(chunks):
        chunk_hash = sha256_text(stable_json_dumps({"doc_id": doc.doc_id, "ordinal": ordinal, "text": text}))
        result.append(
            ChunkRecord(
                chunk_id=f"{doc.doc_id}:chunk:{ordinal}:{chunk_hash[:12]}",
                doc_id=doc.doc_id,
                canonical_group_id=doc.canonical_group_id,
                source=doc.source,
                language=doc.language,
                content_type=doc.content_type,
                officialness=doc.officialness,
                title=doc.title,
                ordinal=ordinal,
                text=text,
                metadata={
                    key: doc.metadata.get(key)
                    for key in [
                        "item_id",
                        "kind",
                        "quest_type",
                        "quest_chapter_num",
                        "quest_chapter_title",
                        "section",
                        "deep_kind",
                        "readable_type",
                    ]
                    if doc.metadata.get(key) is not None
                },
            )
        )
    return result


def _split_long_text(text: str, max_chars: int) -> list[str]:
    return [text[index : index + max_chars] for index in range(0, len(text), max_chars)]
