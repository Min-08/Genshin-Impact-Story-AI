from __future__ import annotations

import json
import re
import shutil
import sqlite3
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

from ..io import ensure_dir, iter_jsonl, pretty_json_dumps, read_json, sha256_text, stable_json_dumps, utc_now, write_json, write_jsonl
from ..normalize import clean_text, extract_text


PROJECT_AMBER = "project_amber"
DIMBREATH_TEXTMAP = "dimbreath_textmap"
OFFICIAL_TEXT = "official"

LANGUAGE_LABELS = {
    "ko": "Korean",
    "en": "English",
    "ja": "Japanese",
    "zh-Hans": "Chinese Simplified",
    "und": "Undetermined",
}

TITLE_FIELDS = ["name", "title", "chapterTitle", "nameFull"]
GENERIC_ROUTE_TITLES = {"", "Other Undefined", "undefined", "none", "null"}

RELIC_SLOT_IDS = {
    "EQUIP_RING": 1,
    "EQUIP_NECKLACE": 2,
    "EQUIP_DRESS": 3,
    "EQUIP_BRACER": 4,
    "EQUIP_SHOES": 5,
}

LIST_DOCUMENT_CONTENT_TYPES = {
    "achievement",
    "elements",
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
}


@dataclass
class V2State:
    items: dict[str, dict[str, Any]] = field(default_factory=dict)
    localizations: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    documents: list[dict[str, Any]] = field(default_factory=list)
    sections: list[dict[str, Any]] = field(default_factory=list)
    text_units: list[dict[str, Any]] = field(default_factory=list)
    relations: list[dict[str, Any]] = field(default_factory=list)
    entity_names: dict[tuple[str, str, str], dict[str, Any]] = field(default_factory=dict)
    title_index: dict[tuple[str, str, str], str] = field(default_factory=dict)
    detail_keys: set[tuple[str, str, str]] = field(default_factory=set)


class ProjectAmberV2Builder:
    def __init__(self, root: Path, *, clean: bool = True) -> None:
        self.root = root.resolve()
        self.clean = clean
        self.raw_root = self.root / "data" / "raw" / PROJECT_AMBER
        self.textmap_root = self.root / "data" / "raw" / DIMBREATH_TEXTMAP
        self.readable_root = self.root / "data" / "processed" / "project_amber_readable_v2"
        self.canonical_root = self.root / "data" / "canonical" / "project_amber_v2"
        self.search_dir = self.root / "data" / "processed" / "search_v2"
        self.search_db = self.search_dir / "project_amber_search.sqlite3"
        self.used_readable_paths: set[Path] = set()
        self.counts: Counter[str] = Counter()
        self.state = V2State()

    def run(self) -> dict[str, Any]:
        if not self.raw_root.exists():
            raise FileNotFoundError(f"Missing Project Amber RAW root: {self.raw_root}")
        if self.clean:
            self._clean_outputs()
        ensure_dir(self.readable_root)
        ensure_dir(self.canonical_root)
        ensure_dir(self.search_dir)

        self._log("index titles and items")
        self._index_titles_and_items()
        self._log("build documents/readable")
        self._build_documents()
        self._log("write canonical jsonl")
        self._write_canonical_files()
        self._log("write textmap jsonl")
        textmap_count = self._write_textmap_entries()
        self._log("build sqlite search")
        search_report = build_project_amber_v2_search(self.canonical_root, self.search_db)

        report = {
            "built_at": utc_now(),
            "version": "0.6.0",
            "source": PROJECT_AMBER,
            "readable_root": str(self.readable_root),
            "canonical_root": str(self.canonical_root),
            "search_db": str(self.search_db),
            "counts": {
                "items": len(self.state.items),
                "localizations": len(self.state.localizations),
                "documents": len(self.state.documents),
                "sections": len(self.state.sections),
                "text_units": len(self.state.text_units),
                "relations": len(self.state.relations),
                "entity_names": len(self.state.entity_names),
                "textmap_entries": textmap_count,
                **dict(sorted(self.counts.items())),
            },
            "raw_project_amber_unchanged": True,
            "raw_integrity_method": "builder writes only to data/processed/project_amber_readable_v2, data/canonical/project_amber_v2, and data/processed/search_v2",
            "search": search_report,
            "notes": [
                "Project Amber is the main corpus.",
                "TextMap is included only as an auxiliary lookup/search table.",
                "Generated v2 files do not overwrite v1 processed/canonical/search outputs.",
            ],
        }
        write_json(self.canonical_root / "build_report.json", report)
        self._log("done")
        return report

    def _log(self, message: str) -> None:
        print(f"[project_amber_v2] {message}", file=sys.stderr, flush=True)

    def _clean_outputs(self) -> None:
        allowed_roots = [
            (self.root / "data" / "processed").resolve(),
            (self.root / "data" / "canonical").resolve(),
        ]
        for path in [self.readable_root, self.canonical_root]:
            resolved = path.resolve()
            if not any(resolved == root or root in resolved.parents for root in allowed_roots):
                raise RuntimeError(f"Refusing to remove unexpected path: {resolved}")
            if resolved.exists():
                shutil.rmtree(resolved)
        ensure_dir(self.search_dir)
        for path in [self.search_db, self.search_dir / "search_report.json"]:
            if path.exists():
                path.unlink()

    def _index_titles_and_items(self) -> None:
        for raw_path in sorted(self.raw_root.glob("*/*/list.raw.json")):
            record = read_json(raw_path)
            language = str(record.get("language") or "und")
            content_type = str(record.get("metadata", {}).get("content_type") or raw_path.parent.name)
            for item_id, item, entity_type in iter_project_amber_list_items(content_type, record.get("payload")):
                canonical_id = canonical_id_for(content_type, item_id, entity_type=entity_type)
                title = title_for_payload(item, language=language, fallback=f"{content_type}-{item_id}")
                route = item.get("route") if isinstance(item, dict) else None
                description = item.get("description") if isinstance(item, dict) else None
                self._add_item(canonical_id, content_type, item_id, item, entity_type=entity_type)
                self._add_localization(
                    canonical_id,
                    language,
                    title=title,
                    description=clean_optional(description),
                    route=clean_optional(route),
                    raw_ref=raw_path,
                    source_url=record.get("source_url"),
                    metadata={"kind": "list", "entity_type": entity_type},
                )
                if title:
                    self.state.title_index[(language, content_type, str(item_id))] = title
                    self._add_entity_name(canonical_id, content_type, language, title, raw_path)

        for raw_path in sorted(self.raw_root.glob("*/*/detail/*.raw.json")):
            record = read_json(raw_path)
            language = str(record.get("language") or "und")
            metadata = record.get("metadata", {})
            content_type = str(metadata.get("content_type") or raw_path.parent.parent.name)
            item_id = str(metadata.get("item_id") or raw_path.stem.removesuffix(".raw"))
            payload = record.get("payload")
            if not isinstance(payload, dict):
                continue
            canonical_id = canonical_id_for(content_type, item_id)
            title = title_for_payload(payload, language=language, fallback=self._indexed_title(language, content_type, item_id))
            self._add_item(canonical_id, content_type, item_id, payload)
            self._add_localization(
                canonical_id,
                language,
                title=title,
                description=clean_optional(payload.get("description")),
                chapter_num=quest_info_field(payload, "chapterNum"),
                chapter_title=quest_info_field(payload, "chapterTitle"),
                route=clean_optional(payload.get("route") or quest_info_field(payload, "route")),
                raw_ref=raw_path,
                source_url=record.get("source_url"),
                metadata={"kind": "detail"},
            )
            self.state.detail_keys.add((language, content_type, item_id))
            if title:
                self.state.title_index[(language, content_type, item_id)] = title
                self._add_entity_name(canonical_id, content_type, language, title, raw_path)

    def _add_item(self, canonical_id: str, content_type: str, item_id: str, payload: Any, *, entity_type: str | None = None) -> None:
        item = self.state.items.setdefault(
            canonical_id,
            {
                "canonical_id": canonical_id,
                "content_type": content_type,
                "item_id": str(item_id),
                "entity_type": entity_type or content_type,
                "icon": None,
                "rank": None,
                "route": None,
                "release": None,
                "metadata": {},
            },
        )
        if isinstance(payload, dict):
            for field_name in ["icon", "rank", "route", "release"]:
                value = payload.get(field_name)
                if value not in (None, "") and item.get(field_name) in (None, ""):
                    item[field_name] = value
            item["metadata"].update(
                {
                    key: value
                    for key, value in payload.items()
                    if key not in {"name", "title", "nameFull", "description", "volume", "storyList", "suit", "items"}
                    and is_json_scalar(value)
                }
            )

    def _add_localization(
        self,
        canonical_id: str,
        language: str,
        *,
        title: str | None,
        raw_ref: Path,
        source_url: str | None,
        description: str | None = None,
        chapter_num: str | None = None,
        chapter_title: str | None = None,
        route: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        key = (canonical_id, language)
        existing = self.state.localizations.get(key)
        row = {
            "canonical_id": canonical_id,
            "language": language,
            "language_label": LANGUAGE_LABELS.get(language, language),
            "title": title,
            "description": description,
            "chapter_num": chapter_num,
            "chapter_title": chapter_title,
            "route": route,
            "source": PROJECT_AMBER,
            "source_url": source_url,
            "raw_ref": str(raw_ref),
            "metadata": metadata or {},
        }
        if existing is None or (not existing.get("title") and title) or row["metadata"].get("kind") == "detail":
            self.state.localizations[key] = row

    def _add_entity_name(self, canonical_id: str, entity_type: str, language: str, name: str, raw_path: Path) -> None:
        normalized = normalize_name(name)
        if not normalized:
            return
        key = (canonical_id, language, normalized)
        self.state.entity_names.setdefault(
            key,
            {
                "canonical_id": canonical_id,
                "entity_type": entity_type,
                "language": language,
                "language_label": LANGUAGE_LABELS.get(language, language),
                "name": name,
                "normalized": normalized,
                "source": PROJECT_AMBER,
                "source_doc_id": None,
                "aliases": [],
                "raw_ref": str(raw_path),
                "metadata": {},
            },
        )

    def _build_documents(self) -> None:
        detail_keys = set(self.state.detail_keys)
        for raw_path in sorted(self.raw_root.glob("*/*/detail/*.raw.json")):
            record = read_json(raw_path)
            self._document_from_detail(record, raw_path)

        for raw_path in sorted(self.raw_root.glob("*/*/deep/**/*.raw.json")):
            record = read_json(raw_path)
            self._documents_from_deep(record, raw_path)

        for raw_path in sorted(self.raw_root.glob("*/*/list.raw.json")):
            record = read_json(raw_path)
            language = str(record.get("language") or "und")
            content_type = str(record.get("metadata", {}).get("content_type") or raw_path.parent.name)
            if content_type not in LIST_DOCUMENT_CONTENT_TYPES:
                for item_id, item, _ in iter_project_amber_list_items(content_type, record.get("payload")):
                    if (language, content_type, str(item_id)) not in detail_keys:
                        self._document_from_list_item(record, raw_path, str(item_id), item)
                continue
            for item_id, item, _ in iter_project_amber_list_items(content_type, record.get("payload")):
                self._document_from_list_item(record, raw_path, str(item_id), item)

    def _document_from_detail(self, record: dict[str, Any], raw_path: Path) -> None:
        metadata = record.get("metadata", {})
        content_type = str(metadata.get("content_type") or raw_path.parent.parent.name)
        item_id = str(metadata.get("item_id") or raw_path.stem.removesuffix(".raw"))
        language = str(record.get("language") or "und")
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return
        canonical_id = canonical_id_for(content_type, item_id)
        title = title_for_payload(payload, language=language, fallback=self._indexed_title(language, content_type, item_id))
        text = extract_text(payload, content_type=content_type)
        if not text:
            text = generic_payload_text(payload)
        if not text:
            return
        document_kind = "detail"
        document_id = f"{canonical_id}:{language}:{document_kind}"
        doc_metadata = {
            "item_id": item_id,
            "kind": "detail",
            **quest_metadata(payload),
        }
        doc = self._add_document(
            document_id=document_id,
            canonical_id=canonical_id,
            language=language,
            content_type=content_type,
            document_kind=document_kind,
            title=title,
            text=text,
            raw_refs=[str(raw_path)],
            source_url=record.get("source_url"),
            metadata=doc_metadata,
        )
        self._write_readable(
            self._readable_path_for_detail(language, content_type, item_id, title, doc_metadata),
            doc,
            payload,
        )

    def _document_from_list_item(self, record: dict[str, Any], raw_path: Path, item_id: str, item: Any) -> None:
        if not isinstance(item, dict):
            return
        language = str(record.get("language") or "und")
        content_type = str(record.get("metadata", {}).get("content_type") or raw_path.parent.name)
        canonical_id = canonical_id_for(content_type, item_id)
        title = title_for_payload(item, language=language, fallback=f"{content_type}-{item_id}")
        text = extract_text(item, content_type=content_type) or generic_payload_text(item)
        if not text:
            return
        document_id = f"{canonical_id}:{language}:list"
        doc = self._add_document(
            document_id=document_id,
            canonical_id=canonical_id,
            language=language,
            content_type=content_type,
            document_kind="list",
            title=title,
            text=text,
            raw_refs=[str(raw_path)],
            source_url=record.get("source_url"),
            metadata={"item_id": item_id, "kind": "list"},
        )
        self._write_readable(
            self._readable_path_for_detail(language, content_type, item_id, title, {"kind": "list"}),
            doc,
            item,
        )

    def _documents_from_deep(self, record: dict[str, Any], raw_path: Path) -> None:
        metadata = record.get("metadata", {})
        if metadata.get("kind") != "deep":
            return
        content_type = str(metadata.get("content_type") or raw_path.parent.parent.parent.name)
        deep_kind = str(metadata.get("deep_kind") or "deep")
        if content_type == "book" and deep_kind == "readable":
            self._book_volume_from_deep(record, raw_path)
        elif content_type == "avatar" and deep_kind == "avatar_fetter":
            self._avatar_fetter_from_deep(record, raw_path)
        elif content_type == "avatar" and deep_kind == "costume_story":
            self._string_deep_from_record(record, raw_path, document_kind="avatar_costume_story")
        elif content_type == "reliquary" and deep_kind == "reliquary_story":
            self._string_deep_from_record(record, raw_path, document_kind="reliquary_piece_story")
        elif content_type == "weapon" and deep_kind == "weapon_story":
            self._string_deep_from_record(record, raw_path, document_kind="weapon_story")
        elif content_type == "material" and deep_kind == "material_story":
            self._string_deep_from_record(record, raw_path, document_kind="material_story")
        else:
            self._string_deep_from_record(record, raw_path, document_kind=deep_kind)

    def _book_volume_from_deep(self, record: dict[str, Any], raw_path: Path) -> None:
        metadata = record.get("metadata", {})
        payload = record.get("payload")
        if not isinstance(payload, str):
            return
        language = str(record.get("language") or "und")
        item_id = str(metadata.get("item_id") or raw_path.parent.name)
        canonical_id = canonical_id_for("book", item_id)
        volume_index = safe_int(metadata.get("volume_index"), default=0)
        volume_id = str(metadata.get("volume_id") or metadata.get("story_id") or metadata.get("deep_id") or volume_index)
        series_title = self._series_title(language, "book", item_id, metadata.get("parent_title"))
        volume_title = clean_optional(metadata.get("title")) or f"volume-{volume_index:02d}"
        title = volume_title
        text = deep_text(metadata, payload, parent_title=series_title, title=volume_title)
        document_id = f"{canonical_id}:{language}:volume:{volume_index:02d}:{safe_id_part(volume_id)}"
        section_id = f"{document_id}:section:volume"
        doc = self._add_document(
            document_id=document_id,
            canonical_id=canonical_id,
            language=language,
            content_type="book",
            document_kind="book_volume",
            title=title,
            text=text,
            raw_refs=[str(raw_path)],
            source_url=record.get("source_url"),
            metadata={
                "item_id": item_id,
                "kind": "deep",
                "deep_kind": "readable",
                "deep_id": metadata.get("deep_id"),
                "volume_index": volume_index,
                "volume_id": volume_id,
                "story_id": metadata.get("story_id"),
                "parent_title": series_title,
            },
        )
        self._add_section(section_id, document_id, canonical_id, language, "book", "book_volume", title, volume_index, text, metadata=doc["metadata"])
        self._add_relation(canonical_id, section_id, "book_has_volume", {"volume_index": volume_index, "volume_id": volume_id})
        path = (
            self.readable_root
            / language
            / "book"
            / safe_path_part(f"{item_id} - {series_title}", max_length=56)
            / f"{safe_path_part(f'{volume_index:02d} - {volume_id} - {volume_title}', max_length=72)}.json"
        )
        self._write_readable(path, doc, payload)

    def _avatar_fetter_from_deep(self, record: dict[str, Any], raw_path: Path) -> None:
        metadata = record.get("metadata", {})
        payload = record.get("payload")
        if not isinstance(payload, dict):
            return
        language = str(record.get("language") or "und")
        item_id = str(metadata.get("item_id") or raw_path.parent.name)
        canonical_id = canonical_id_for("avatar", item_id)
        character_name = self._series_title(language, "avatar", item_id, metadata.get("title"))
        for section_name, document_kind, file_name in [
            ("story", "avatar_stories", "stories.json"),
            ("quotes", "avatar_quotes", "quotes.json"),
        ]:
            rows = payload.get(section_name)
            if not isinstance(rows, dict):
                continue
            text = avatar_section_text(rows)
            title = f"{character_name} {section_name}"
            empty_section = not text
            if empty_section:
                text = f"title: {title}"
            document_metadata = {
                "item_id": item_id,
                "kind": "deep",
                "deep_kind": "avatar_fetter",
                "section": section_name,
                "empty_section": empty_section,
            }
            document_id = f"{canonical_id}:{language}:{document_kind}"
            doc = self._add_document(
                document_id=document_id,
                canonical_id=canonical_id,
                language=language,
                content_type="avatar",
                document_kind=document_kind,
                title=title,
                text=text,
                raw_refs=[str(raw_path)],
                source_url=record.get("source_url"),
                metadata=document_metadata,
            )
            if empty_section:
                section_id = f"{document_id}:section:empty"
                self._add_section(section_id, document_id, canonical_id, language, "avatar", section_name, title, 0, text, metadata=document_metadata)
                self._add_relation(canonical_id, section_id, f"avatar_has_{section_name.rstrip('s')}", {"ordinal": 0, "empty_section": True})
            else:
                for ordinal, row in enumerate(sorted_rows(rows)):
                    row_title = clean_optional(row.get("title")) or clean_optional(row.get("title2")) or f"{section_name}-{ordinal}"
                    row_text = avatar_row_text(row)
                    if not row_text:
                        continue
                    section_id = f"{document_id}:section:{ordinal}"
                    self._add_section(section_id, document_id, canonical_id, language, "avatar", section_name, row_title, ordinal, row_text, metadata={"row_id": row.get("id")})
                    self._add_relation(canonical_id, section_id, f"avatar_has_{section_name.rstrip('s')}", {"ordinal": ordinal})
            path = self.readable_root / language / "avatar" / safe_path_part(f"{item_id} - {character_name}", max_length=56) / file_name
            self._write_readable(path, doc, payload.get(section_name))

    def _string_deep_from_record(self, record: dict[str, Any], raw_path: Path, *, document_kind: str) -> None:
        metadata = record.get("metadata", {})
        payload = record.get("payload")
        if not isinstance(payload, str):
            return
        language = str(record.get("language") or "und")
        content_type = str(metadata.get("content_type") or raw_path.parent.parent.parent.name)
        item_id = str(metadata.get("item_id") or raw_path.parent.name)
        canonical_id = canonical_id_for(content_type, item_id)
        title = clean_optional(metadata.get("title")) or self._indexed_title(language, content_type, item_id)
        parent_title = self._series_title(language, content_type, item_id, metadata.get("parent_title") or title)
        text = deep_text(metadata, payload, parent_title=parent_title, title=title)
        deep_id = str(metadata.get("deep_id") or document_kind)
        document_id = f"{canonical_id}:{language}:deep:{safe_id_part(document_kind)}:{safe_id_part(deep_id)}"
        doc = self._add_document(
            document_id=document_id,
            canonical_id=canonical_id,
            language=language,
            content_type=content_type,
            document_kind=document_kind,
            title=title,
            text=text,
            raw_refs=[str(raw_path)],
            source_url=record.get("source_url"),
            metadata={
                "item_id": item_id,
                "kind": "deep",
                "deep_kind": metadata.get("deep_kind"),
                "deep_id": metadata.get("deep_id"),
                "story_id": metadata.get("story_id"),
                "story_index": metadata.get("story_index"),
                "costume_index": metadata.get("costume_index"),
                "slot": metadata.get("slot"),
                "slot_id": metadata.get("slot_id"),
                "parent_title": parent_title,
            },
        )
        ordinal = safe_int(metadata.get("story_index"), default=safe_int(metadata.get("slot_id"), default=safe_int(metadata.get("costume_index"), default=0)))
        section_id = f"{document_id}:section:0"
        self._add_section(section_id, document_id, canonical_id, language, content_type, document_kind, title, ordinal, text, metadata=doc["metadata"])
        self._add_relation(canonical_id, section_id, relation_for_document_kind(document_kind), doc["metadata"])
        self._write_readable(self._readable_path_for_deep(language, content_type, item_id, parent_title, title, metadata, document_kind), doc, payload)

    def _add_document(
        self,
        *,
        document_id: str,
        canonical_id: str,
        language: str,
        content_type: str,
        document_kind: str,
        title: str | None,
        text: str,
        raw_refs: list[str],
        source_url: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        row = {
            "document_id": document_id,
            "canonical_id": canonical_id,
            "language": language,
            "language_label": LANGUAGE_LABELS.get(language, language),
            "content_type": content_type,
            "document_kind": document_kind,
            "title": title,
            "text": clean_text(text),
            "text_hash": sha256_text(clean_text(text)),
            "source": PROJECT_AMBER,
            "source_url": source_url,
            "officialness": OFFICIAL_TEXT,
            "raw_refs": raw_refs,
            "metadata": clean_metadata(metadata),
        }
        self.state.documents.append(row)
        self.counts[f"documents:{content_type}:{document_kind}"] += 1
        self._add_text_units_for_document(row)
        return row

    def _add_section(
        self,
        section_id: str,
        document_id: str,
        canonical_id: str,
        language: str,
        content_type: str,
        section_type: str,
        title: str | None,
        ordinal: int,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.state.sections.append(
            {
                "section_id": section_id,
                "document_id": document_id,
                "canonical_id": canonical_id,
                "language": language,
                "language_label": LANGUAGE_LABELS.get(language, language),
                "content_type": content_type,
                "section_type": section_type,
                "title": title,
                "ordinal": ordinal,
                "text": clean_text(text),
                "text_hash": sha256_text(clean_text(text)),
                "metadata": clean_metadata(metadata or {}),
            }
        )

    def _add_text_units_for_document(self, doc: dict[str, Any]) -> None:
        for ordinal, text in enumerate(split_text_units(doc["text"])):
            speaker, unit_text = split_speaker(text)
            if not unit_text:
                continue
            unit_id = f"{doc['document_id']}:unit:{ordinal}"
            self.state.text_units.append(
                {
                    "unit_id": unit_id,
                    "document_id": doc["document_id"],
                    "canonical_id": doc["canonical_id"],
                    "section_id": None,
                    "language": doc["language"],
                    "language_label": doc["language_label"],
                    "content_type": doc["content_type"],
                    "document_kind": doc["document_kind"],
                    "title": doc["title"],
                    "speaker": speaker,
                    "ordinal": ordinal,
                    "text": unit_text,
                    "text_hash": sha256_text(unit_text),
                    "source": PROJECT_AMBER,
                    "source_url": doc.get("source_url"),
                    "raw_refs": doc.get("raw_refs") or [],
                    "metadata": doc.get("metadata") or {},
                }
            )

    def _add_relation(self, source_id: str, target_id: str, relation_type: str, metadata: dict[str, Any] | None = None) -> None:
        self.state.relations.append(
            {
                "relation_id": f"{relation_type}:{source_id}:{target_id}",
                "source_id": source_id,
                "target_id": target_id,
                "relation_type": relation_type,
                "source": PROJECT_AMBER,
                "metadata": clean_metadata(metadata or {}),
            }
        )

    def _readable_path_for_detail(self, language: str, content_type: str, item_id: str, title: str | None, metadata: dict[str, Any]) -> Path:
        display_title = title or f"{content_type}-{item_id}"
        filename = safe_path_part(f"{item_id} - {display_title}", max_length=82) + ".json"
        if content_type == "quest":
            quest_type = str(metadata.get("quest_type") or "other")
            return self.readable_root / language / "quest" / quest_type / filename
        return self.readable_root / language / content_type / filename

    def _readable_path_for_deep(
        self,
        language: str,
        content_type: str,
        item_id: str,
        parent_title: str | None,
        title: str | None,
        metadata: dict[str, Any],
        document_kind: str,
    ) -> Path:
        folder = self.readable_root / language / content_type / safe_path_part(f"{item_id} - {parent_title or content_type}", max_length=56)
        display_title = title or str(metadata.get("deep_id") or document_kind)
        if document_kind == "reliquary_piece_story":
            slot_id = safe_int(metadata.get("slot_id"), default=0)
            slot = str(metadata.get("slot") or "slot")
            return folder / "pieces" / f"{safe_path_part(f'{slot_id} - {slot} - {display_title}', max_length=72)}.json"
        if document_kind == "weapon_story":
            story_index = safe_int(metadata.get("story_index"), default=0)
            return folder / "story" / f"{safe_path_part(f'{story_index:02d} - {display_title}', max_length=72)}.json"
        if document_kind == "material_story":
            story_index = safe_int(metadata.get("story_index"), default=0)
            return folder / "story" / f"{safe_path_part(f'{story_index:02d} - {display_title}', max_length=72)}.json"
        if document_kind == "avatar_costume_story":
            costume_index = safe_int(metadata.get("costume_index"), default=0)
            return folder / "costumes" / f"{safe_path_part(f'{costume_index:02d} - {display_title}', max_length=72)}.json"
        return folder / f"{safe_path_part(f'{document_kind} - {display_title}', max_length=72)}.json"

    def _write_readable(self, path: Path, document: dict[str, Any], payload: Any) -> None:
        path = self._unique_readable_path(path)
        ensure_dir(path.parent)
        output = {
            "title": document.get("title"),
            "language": document.get("language"),
            "content_type": document.get("content_type"),
            "document_kind": document.get("document_kind"),
            "canonical_id": document.get("canonical_id"),
            "document_id": document.get("document_id"),
            "source": document.get("source"),
            "source_url": document.get("source_url"),
            "raw_refs": document.get("raw_refs"),
            "metadata": document.get("metadata"),
            "text": document.get("text"),
            "payload": payload,
        }
        path.write_text(pretty_json_dumps(output) + "\n", encoding="utf-8")

    def _unique_readable_path(self, path: Path) -> Path:
        if path not in self.used_readable_paths and not path.exists():
            self.used_readable_paths.add(path)
            return path
        stem = path.stem
        suffix = path.suffix
        index = 2
        while True:
            candidate = path.with_name(f"{stem} ({index}){suffix}")
            if candidate not in self.used_readable_paths and not candidate.exists():
                self.used_readable_paths.add(candidate)
                return candidate
            index += 1

    def _series_title(self, language: str, content_type: str, item_id: str, candidate: Any) -> str:
        title = clean_optional(candidate) or self._indexed_title(language, content_type, item_id)
        if is_generic_title(title):
            if content_type == "book":
                return "unnamed_book"
            return f"unnamed_{content_type}"
        return title or f"{content_type}-{item_id}"

    def _indexed_title(self, language: str, content_type: str, item_id: str) -> str | None:
        return self.state.title_index.get((language, content_type, str(item_id))) or self.state.title_index.get(("en", content_type, str(item_id)))

    def _write_canonical_files(self) -> None:
        write_jsonl(self.canonical_root / "items.jsonl", self.state.items.values())
        write_jsonl(self.canonical_root / "localizations.jsonl", self.state.localizations.values())
        write_jsonl(self.canonical_root / "documents.jsonl", self.state.documents)
        write_jsonl(self.canonical_root / "sections.jsonl", self.state.sections)
        write_jsonl(self.canonical_root / "text_units.jsonl", self.state.text_units)
        write_jsonl(self.canonical_root / "relations.jsonl", self.state.relations)
        write_jsonl(self.canonical_root / "entity_names.jsonl", self.state.entity_names.values())

    def _write_textmap_entries(self) -> int:
        path = self.canonical_root / "textmap_entries.jsonl"
        ensure_dir(path.parent)
        count = 0
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            if self.textmap_root.exists():
                for raw_path in sorted(self.textmap_root.glob("*/*.raw.json")):
                    record = read_json(raw_path)
                    language = str(record.get("language") or raw_path.parent.name)
                    payload = record.get("payload")
                    if not isinstance(payload, dict):
                        continue
                    for textmap_id, text in payload.items():
                        if not isinstance(text, str):
                            continue
                        cleaned = clean_text(text)
                        if not cleaned:
                            continue
                        row = {
                            "textmap_id": str(textmap_id),
                            "language": language,
                            "language_label": LANGUAGE_LABELS.get(language, language),
                            "text": cleaned,
                            "text_hash": sha256_text(cleaned),
                            "source": DIMBREATH_TEXTMAP,
                            "source_url": record.get("source_url"),
                            "raw_ref": str(raw_path),
                            "metadata": {},
                        }
                        handle.write(stable_json_dumps(row) + "\n")
                        count += 1
        return count


def build_project_amber_v2(root: Path, *, clean: bool = True) -> dict[str, Any]:
    return ProjectAmberV2Builder(root, clean=clean).run()


def iter_project_amber_list_items(content_type: str, payload: Any) -> Iterator[tuple[str, dict[str, Any], str]]:
    if not isinstance(payload, dict):
        return
    if content_type == "achievement":
        for group_id, group in sorted(payload.items(), key=lambda pair: str(pair[0])):
            if not isinstance(group, dict):
                continue
            group_item = {key: value for key, value in group.items() if key != "achievementList"}
            group_item.setdefault("id", group_id)
            yield str(group_id), group_item, "achievement_group"
            achievements = group.get("achievementList")
            achievement_rows = achievements.items() if isinstance(achievements, dict) else enumerate(achievements or [])
            for achievement_key, achievement in achievement_rows:
                if not isinstance(achievement, dict):
                    continue
                details = achievement.get("details")
                detail_rows = details if isinstance(details, list) and details else [achievement]
                for detail in detail_rows:
                    if not isinstance(detail, dict):
                        continue
                    achievement_id = str(detail.get("id") or achievement.get("id") or achievement_key)
                    merged = {**achievement, "detail": detail, "group": group_item}
                    yield achievement_id, merged, "achievement"
        return
    if content_type == "elements":
        info = payload.get("info")
        if isinstance(info, dict):
            yield "info", info, "elements_info"
        for section in ["resonance", "tutorials", "tips"]:
            rows = payload.get(section)
            if isinstance(rows, dict):
                for item_id, item in sorted(rows.items(), key=lambda pair: str(pair[0])):
                    if isinstance(item, dict):
                        yield f"{section}:{item_id}", item, f"elements_{section}"
        return
    items = payload.get("items")
    if isinstance(items, dict):
        for item_id, item in sorted(items.items(), key=lambda pair: str(pair[0])):
            if isinstance(item, dict):
                yield str(item_id), item, content_type
        return
    for item_id, item in sorted(payload.items(), key=lambda pair: str(pair[0])):
        if isinstance(item, dict):
            yield str(item_id), item, content_type
        else:
            yield str(item_id), {"id": item_id, "value": item}, content_type


def canonical_id_for(content_type: str, item_id: str, *, entity_type: str | None = None) -> str:
    if entity_type == "achievement_group":
        return f"{PROJECT_AMBER}:achievement_group:{item_id}"
    return f"{PROJECT_AMBER}:{content_type}:{item_id}"


def title_for_payload(payload: Any, *, language: str, fallback: str | None = None) -> str | None:
    if not isinstance(payload, dict):
        return fallback
    info = payload.get("info")
    if isinstance(info, dict):
        chapter_num = clean_optional(info.get("chapterNum"))
        chapter_title = clean_optional(info.get("chapterTitle"))
        route = clean_optional(info.get("route"))
        if chapter_num and chapter_title:
            return f"{chapter_num} - {chapter_title}"
        if chapter_title:
            return chapter_title
        if route:
            return route
    for field in TITLE_FIELDS:
        value = payload.get(field)
        if isinstance(value, str) and value.strip():
            return clean_text(value)
        if isinstance(value, dict):
            text = multilingual_text(value, language)
            if text:
                return text
    detail = payload.get("detail")
    if isinstance(detail, dict):
        nested = title_for_payload(detail, language=language)
        if nested:
            return nested
    route = clean_optional(payload.get("route"))
    if route:
        return route
    value = payload.get("value")
    if isinstance(value, str) and value.strip():
        return clean_text(value)
    return fallback


def multilingual_text(value: dict[str, Any], language: str) -> str | None:
    order = {
        "ko": ["KR", "ko", "EN", "en", "JP", "ja", "CHS", "zh-Hans"],
        "en": ["EN", "en", "KR", "ko", "JP", "ja", "CHS", "zh-Hans"],
        "ja": ["JP", "ja", "EN", "en", "KR", "ko", "CHS", "zh-Hans"],
        "zh-Hans": ["CHS", "zh-Hans", "EN", "en", "KR", "ko", "JP", "ja"],
    }.get(language, ["KR", "ko", "EN", "en", "JP", "ja", "CHS", "zh-Hans"])
    for key in order:
        text = value.get(key)
        if isinstance(text, str) and text.strip():
            return clean_text(text)
    for text in value.values():
        if isinstance(text, str) and text.strip():
            return clean_text(text)
    return None


def clean_optional(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return clean_text(value)
    return None


def quest_info_field(payload: dict[str, Any], field_name: str) -> str | None:
    info = payload.get("info")
    if isinstance(info, dict):
        return clean_optional(info.get(field_name))
    return None


def quest_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    info = payload.get("info")
    if not isinstance(info, dict):
        return {}
    return {
        "quest_type": info.get("type"),
        "quest_chapter_num": info.get("chapterNum"),
        "quest_chapter_title": info.get("chapterTitle"),
        "route": info.get("route"),
    }


def generic_payload_text(payload: Any) -> str:
    lines: list[str] = []

    def walk(value: Any, path: list[str]) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"icon", "raw_ref", "metadata"}:
                    continue
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
        else:
            text = str(value)
        label = ".".join(path)
        lines.append(f"{label}: {text}" if label else text)

    walk(payload, [])
    return "\n".join(dedupe_keep_order(lines))


def deep_text(metadata: dict[str, Any], payload: str, *, parent_title: str | None, title: str | None) -> str:
    lines = []
    if parent_title:
        lines.append(f"parentTitle: {parent_title}")
    if title:
        lines.append(f"title: {title}")
    description = clean_optional(metadata.get("description"))
    if description:
        lines.append(f"description: {description}")
    lines.append(payload)
    return "\n".join(dedupe_keep_order(clean_text(line) for line in lines if clean_text(line)))


def avatar_section_text(rows: dict[str, Any]) -> str:
    return "\n".join(row_text for row in sorted_rows(rows) if (row_text := avatar_row_text(row)))


def avatar_row_text(row: dict[str, Any]) -> str:
    lines = []
    for key in ["title", "tips", "text", "title2", "text2"]:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            if key in {"title", "title2", "tips"}:
                lines.append(f"{key}: {value}")
            else:
                lines.append(value)
    return "\n".join(dedupe_keep_order(clean_text(line) for line in lines))


def sorted_rows(rows: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for _, row in sorted(rows.items(), key=lambda pair: sort_key(pair[0])):
        if isinstance(row, dict):
            yield row


def sort_key(value: Any) -> tuple[int, str]:
    text = str(value)
    return (int(text), text) if text.isdigit() else (999999, text)


def split_text_units(text: str) -> list[str]:
    normalized = clean_text(text)
    if not normalized:
        return []
    units: list[str] = []
    for block in re.split(r"\n\s*\n", normalized):
        block = block.strip()
        if not block:
            continue
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if all(len(line) <= 260 for line in lines) and len(lines) > 1:
            units.extend(lines)
        else:
            units.append("\n".join(lines))
    return units


def split_speaker(text: str) -> tuple[str | None, str]:
    match = re.match(r"^([^:\n]{1,60}):\s+(.+)$", text, flags=re.DOTALL)
    if match:
        speaker = match.group(1).strip()
        if speaker and speaker not in {"title", "description", "parentTitle", "role", "tips"}:
            return speaker, match.group(2).strip()
    return None, text.strip()


def relation_for_document_kind(document_kind: str) -> str:
    if document_kind == "reliquary_piece_story":
        return "reliquary_has_piece"
    if document_kind == "avatar_costume_story":
        return "avatar_has_costume"
    return "item_has_story"


def safe_path_part(value: Any, *, max_length: int = 120) -> str:
    text = clean_text(str(value)).replace("\n", " ")
    for char in '<>:"/\\|?*':
        text = text.replace(char, " ")
    text = " ".join(text.split()).rstrip(" .")
    if len(text) > max_length:
        text = text[:max_length].rstrip(" .")
    return text or "unknown"


def safe_id_part(value: Any) -> str:
    return re.sub(r"[^\w.\-:]+", "_", str(value), flags=re.UNICODE).strip("._") or "unknown"


def safe_int(value: Any, *, default: int) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def is_generic_title(value: str | None) -> bool:
    if value is None:
        return True
    return value.strip() in GENERIC_ROUTE_TITLES


def is_json_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def clean_metadata(value: dict[str, Any]) -> dict[str, Any]:
    return {key: item for key, item in value.items() if item is not None}


def normalize_name(value: str) -> str:
    return clean_text(value).casefold()


def dedupe_keep_order(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        text = clean_text(value)
        if not text:
            continue
        digest = sha256_text(text)
        if digest in seen:
            continue
        seen.add(digest)
        result.append(text)
    return result


def raw_fingerprint(raw_root: Path) -> dict[str, Any]:
    files = sorted(path for path in raw_root.rglob("*") if path.is_file())
    parts = []
    total_bytes = 0
    for path in files:
        stat = path.stat()
        total_bytes += stat.st_size
        parts.append(f"{path.relative_to(raw_root).as_posix()}\0{stat.st_size}\0{stat.st_mtime_ns}")
    return {
        "root": str(raw_root.resolve()),
        "files": len(files),
        "bytes": total_bytes,
        "fingerprint_sha256": sha256_text("\n".join(parts)),
    }


def sha256_file(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_project_amber_v2_search(canonical_root: Path, db_path: Path) -> dict[str, Any]:
    ensure_dir(db_path.parent)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")
    create_v2_schema(conn)
    counts = {
        "items": insert_json_rows(conn, "items", canonical_root / "items.jsonl", item_columns()),
        "localizations": insert_json_rows(conn, "localizations", canonical_root / "localizations.jsonl", localization_columns()),
        "documents": insert_json_rows(conn, "documents", canonical_root / "documents.jsonl", document_columns()),
        "sections": insert_json_rows(conn, "sections", canonical_root / "sections.jsonl", section_columns()),
        "text_units": insert_json_rows(conn, "text_units", canonical_root / "text_units.jsonl", text_unit_columns()),
        "relations": insert_json_rows(conn, "relations", canonical_root / "relations.jsonl", relation_columns()),
        "textmap_entries": insert_json_rows(conn, "textmap_entries", canonical_root / "textmap_entries.jsonl", textmap_columns()),
    }
    populate_v2_fts(conn)
    conn.execute("PRAGMA optimize")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    report = {
        "built_at": utc_now(),
        "db_path": str(db_path),
        "db_size_bytes": db_path.stat().st_size,
        "sqlite_integrity_check": integrity,
        **counts,
        "fts": {
            "text_units_unicode": True,
            "text_units_trigram": True,
            "textmap_unicode": True,
            "textmap_trigram": True,
        },
    }
    write_json(db_path.parent / "search_report.json", report)
    return report


def create_v2_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE items (
            canonical_id TEXT PRIMARY KEY,
            content_type TEXT NOT NULL,
            item_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            icon TEXT,
            rank TEXT,
            route TEXT,
            release TEXT,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE localizations (
            canonical_id TEXT NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            title TEXT,
            description TEXT,
            chapter_num TEXT,
            chapter_title TEXT,
            route TEXT,
            source TEXT NOT NULL,
            source_url TEXT,
            raw_ref TEXT,
            metadata_json TEXT NOT NULL,
            PRIMARY KEY (canonical_id, language)
        );

        CREATE TABLE documents (
            document_id TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            content_type TEXT NOT NULL,
            document_kind TEXT NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            officialness TEXT NOT NULL,
            raw_refs_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE sections (
            section_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            content_type TEXT NOT NULL,
            section_type TEXT NOT NULL,
            title TEXT,
            ordinal INTEGER NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE text_units (
            rowid INTEGER PRIMARY KEY,
            unit_id TEXT UNIQUE NOT NULL,
            document_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            section_id TEXT,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            content_type TEXT NOT NULL,
            document_kind TEXT NOT NULL,
            title TEXT,
            speaker TEXT,
            ordinal INTEGER NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            raw_refs_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE relations (
            relation_id TEXT PRIMARY KEY,
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            source TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE textmap_entries (
            rowid INTEGER PRIMARY KEY,
            textmap_id TEXT NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            source TEXT NOT NULL,
            source_url TEXT,
            raw_ref TEXT,
            metadata_json TEXT NOT NULL
        );

        CREATE INDEX idx_units_canonical ON text_units(canonical_id);
        CREATE INDEX idx_units_language ON text_units(language);
        CREATE INDEX idx_units_content_type ON text_units(content_type);
        CREATE INDEX idx_units_document_kind ON text_units(document_kind);
        CREATE INDEX idx_documents_canonical ON documents(canonical_id);
        CREATE INDEX idx_textmap_language ON textmap_entries(language);
        CREATE INDEX idx_textmap_id ON textmap_entries(textmap_id);

        CREATE VIRTUAL TABLE text_units_fts_unicode USING fts5(
            unit_id UNINDEXED,
            title,
            speaker,
            text,
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE VIRTUAL TABLE text_units_fts_trigram USING fts5(
            unit_id UNINDEXED,
            title,
            speaker,
            text,
            tokenize='trigram'
        );

        CREATE VIRTUAL TABLE textmap_fts_unicode USING fts5(
            entry_rowid UNINDEXED,
            text,
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE VIRTUAL TABLE textmap_fts_trigram USING fts5(
            entry_rowid UNINDEXED,
            text,
            tokenize='trigram'
        );
        """
    )


def insert_json_rows(conn: sqlite3.Connection, table: str, path: Path, columns: list[tuple[str, str]]) -> int:
    if not path.exists():
        return 0
    names = [name for name, _ in columns]
    placeholders = ", ".join("?" for _ in names)
    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(names)}) VALUES ({placeholders})"
    rows = []
    count = 0
    for row in iter_jsonl(path):
        rows.append(tuple(column_value(row, source_key) for _, source_key in columns))
        if len(rows) >= 2000:
            conn.executemany(sql, rows)
            count += len(rows)
            rows.clear()
    if rows:
        conn.executemany(sql, rows)
        count += len(rows)
    conn.commit()
    return count


def populate_v2_fts(conn: sqlite3.Connection) -> None:
    unit_sql = "INSERT INTO {table} (unit_id, title, speaker, text) VALUES (?, ?, ?, ?)"
    for table in ["text_units_fts_unicode", "text_units_fts_trigram"]:
        rows = []
        for row in conn.execute("SELECT unit_id, title, speaker, text FROM text_units"):
            rows.append((row[0], row[1], row[2], row[3]))
            if len(rows) >= 5000:
                conn.executemany(unit_sql.format(table=table), rows)
                rows.clear()
        if rows:
            conn.executemany(unit_sql.format(table=table), rows)
        conn.commit()

    textmap_sql = "INSERT INTO {table} (entry_rowid, text) VALUES (?, ?)"
    for table in ["textmap_fts_unicode", "textmap_fts_trigram"]:
        rows = []
        for row in conn.execute("SELECT rowid, text FROM textmap_entries"):
            rows.append((row[0], row[1]))
            if len(rows) >= 5000:
                conn.executemany(textmap_sql.format(table=table), rows)
                rows.clear()
        if rows:
            conn.executemany(textmap_sql.format(table=table), rows)
        conn.commit()


def column_value(row: dict[str, Any], key: str) -> Any:
    if key.endswith("_json"):
        source_key = key.removesuffix("_json")
        if source_key == "raw_refs":
            source_key = "raw_refs"
        if source_key == "metadata":
            source_key = "metadata"
        return stable_json_dumps(row.get(source_key) or ([] if source_key == "raw_refs" else {}))
    value = row.get(key)
    if isinstance(value, (list, dict)):
        return stable_json_dumps(value)
    return value


def item_columns() -> list[tuple[str, str]]:
    return [
        ("canonical_id", "canonical_id"),
        ("content_type", "content_type"),
        ("item_id", "item_id"),
        ("entity_type", "entity_type"),
        ("icon", "icon"),
        ("rank", "rank"),
        ("route", "route"),
        ("release", "release"),
        ("metadata_json", "metadata_json"),
    ]


def localization_columns() -> list[tuple[str, str]]:
    return [
        ("canonical_id", "canonical_id"),
        ("language", "language"),
        ("language_label", "language_label"),
        ("title", "title"),
        ("description", "description"),
        ("chapter_num", "chapter_num"),
        ("chapter_title", "chapter_title"),
        ("route", "route"),
        ("source", "source"),
        ("source_url", "source_url"),
        ("raw_ref", "raw_ref"),
        ("metadata_json", "metadata_json"),
    ]


def document_columns() -> list[tuple[str, str]]:
    return [
        ("document_id", "document_id"),
        ("canonical_id", "canonical_id"),
        ("language", "language"),
        ("language_label", "language_label"),
        ("content_type", "content_type"),
        ("document_kind", "document_kind"),
        ("title", "title"),
        ("text", "text"),
        ("text_hash", "text_hash"),
        ("source", "source"),
        ("source_url", "source_url"),
        ("officialness", "officialness"),
        ("raw_refs_json", "raw_refs_json"),
        ("metadata_json", "metadata_json"),
    ]


def section_columns() -> list[tuple[str, str]]:
    return [
        ("section_id", "section_id"),
        ("document_id", "document_id"),
        ("canonical_id", "canonical_id"),
        ("language", "language"),
        ("language_label", "language_label"),
        ("content_type", "content_type"),
        ("section_type", "section_type"),
        ("title", "title"),
        ("ordinal", "ordinal"),
        ("text", "text"),
        ("text_hash", "text_hash"),
        ("metadata_json", "metadata_json"),
    ]


def text_unit_columns() -> list[tuple[str, str]]:
    return [
        ("unit_id", "unit_id"),
        ("document_id", "document_id"),
        ("canonical_id", "canonical_id"),
        ("section_id", "section_id"),
        ("language", "language"),
        ("language_label", "language_label"),
        ("content_type", "content_type"),
        ("document_kind", "document_kind"),
        ("title", "title"),
        ("speaker", "speaker"),
        ("ordinal", "ordinal"),
        ("text", "text"),
        ("text_hash", "text_hash"),
        ("source", "source"),
        ("source_url", "source_url"),
        ("raw_refs_json", "raw_refs_json"),
        ("metadata_json", "metadata_json"),
    ]


def relation_columns() -> list[tuple[str, str]]:
    return [
        ("relation_id", "relation_id"),
        ("source_id", "source_id"),
        ("target_id", "target_id"),
        ("relation_type", "relation_type"),
        ("source", "source"),
        ("metadata_json", "metadata_json"),
    ]


def textmap_columns() -> list[tuple[str, str]]:
    return [
        ("textmap_id", "textmap_id"),
        ("language", "language"),
        ("language_label", "language_label"),
        ("text", "text"),
        ("text_hash", "text_hash"),
        ("source", "source"),
        ("source_url", "source_url"),
        ("raw_ref", "raw_ref"),
        ("metadata_json", "metadata_json"),
    ]


def search_project_amber_v2(
    db_path: Path,
    query: str,
    *,
    language: str | None = None,
    content_type: str | None = None,
    limit: int = 10,
    mode: str = "unicode",
    include_textmap: bool = False,
) -> list[dict[str, Any]]:
    table = "text_units_fts_trigram" if mode == "trigram" else "text_units_fts_unicode"
    match = fts_query(query, mode=mode)
    filters = []
    params: list[Any] = [match]
    if language:
        filters.append("u.language = ?")
        params.append(language)
    if content_type:
        filters.append("u.content_type = ?")
        params.append(content_type)
    where = f"{table} MATCH ?"
    if filters:
        where += " AND " + " AND ".join(filters)
    sql = f"""
        SELECT
            'text_unit' AS result_type,
            u.unit_id AS id,
            u.unit_id,
            u.document_id,
            u.canonical_id,
            u.language,
            u.language_label,
            u.content_type,
            u.document_kind,
            u.title,
            u.speaker,
            u.ordinal,
            u.text,
            u.source,
            u.source_url,
            u.raw_refs_json,
            u.metadata_json,
            bm25({table}) AS rank
        FROM {table}
        JOIN text_units u ON u.unit_id = {table}.unit_id
        WHERE {where}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [decode_search_row(dict(row)) for row in conn.execute(sql, params).fetchall()]
    if include_textmap:
        rows.extend(search_v2_textmap(conn, query, language=language, mode=mode, limit=limit))
        rows.sort(key=lambda row: row.get("rank", 0))
        rows = rows[:limit]
    conn.close()
    return rows


def search_v2_textmap(conn: sqlite3.Connection, query: str, *, language: str | None, mode: str, limit: int) -> list[dict[str, Any]]:
    table = "textmap_fts_trigram" if mode == "trigram" else "textmap_fts_unicode"
    params: list[Any] = [fts_query(query, mode=mode)]
    filters = []
    if language:
        filters.append("t.language = ?")
        params.append(language)
    where = f"{table} MATCH ?"
    if filters:
        where += " AND " + " AND ".join(filters)
    sql = f"""
        SELECT
            'textmap' AS result_type,
            t.textmap_id AS id,
            t.textmap_id,
            t.language,
            t.language_label,
            t.text,
            t.source,
            t.source_url,
            t.raw_ref,
            t.metadata_json,
            bm25({table}) AS rank
        FROM {table}
        JOIN textmap_entries t ON t.rowid = {table}.entry_rowid
        WHERE {where}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)
    return [decode_search_row(dict(row)) for row in conn.execute(sql, params).fetchall()]


def decode_search_row(row: dict[str, Any]) -> dict[str, Any]:
    for key in ["raw_refs_json", "metadata_json"]:
        if key in row:
            out_key = key.removesuffix("_json")
            try:
                row[out_key] = json.loads(row[key]) if row[key] else None
            except json.JSONDecodeError:
                row[out_key] = None
            del row[key]
    return row


def fts_query(query: str, *, mode: str = "unicode") -> str:
    cleaned = clean_text(query)
    if not cleaned:
        return '""'
    if mode == "trigram":
        return f'"{cleaned.replace(chr(34), chr(34) + chr(34))}"'
    tokens = [token.strip() for token in query.split() if token.strip()]
    if not tokens:
        return '""'
    return " AND ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens)
