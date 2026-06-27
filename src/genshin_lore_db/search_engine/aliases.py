from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from genshin_lore_db.io import ensure_dir, iter_jsonl, read_json, sha256_text, stable_json_dumps, write_json, write_jsonl
from genshin_lore_db.normalize import clean_text


LANGUAGE_LABELS = {
    "ko": "한국어",
    "zh-Hans": "중국어_간체",
    "ja": "일본어",
    "en": "영어",
    "und": "공통",
}


def build_entity_aliases(root: Path) -> dict[str, Any]:
    root = root.resolve()
    canonical_entity_path = root / "data" / "canonical" / "entity_names.jsonl"
    rag_documents_path = root / "data" / "processed" / "rag" / "documents.jsonl"
    manual_concepts_path = root / "config" / "search_engine_manual_concepts.json"
    out_dir = root / "data" / "processed" / "entities"
    ensure_dir(out_dir)

    concepts: dict[str, dict[str, Any]] = {}

    if canonical_entity_path.exists():
        for row in iter_jsonl(canonical_entity_path):
            canonical_id = str(row.get("canonical_id") or "").strip()
            if not canonical_id:
                continue
            concept = concepts.setdefault(canonical_id, new_concept(canonical_id))
            concept["entity_types"][str(row.get("entity_type") or "unknown")] += 1
            concept["sources"][str(row.get("source") or "unknown")] += 1
            add_alias(
                concept,
                name=row.get("name"),
                language=str(row.get("language") or "und"),
                source=str(row.get("source") or "unknown"),
                alias_source="entity_names",
                weight=10.0,
            )
            for alias in row.get("aliases") or []:
                add_alias(
                    concept,
                    name=alias,
                    language=str(row.get("language") or "und"),
                    source=str(row.get("source") or "unknown"),
                    alias_source="entity_names.aliases",
                    weight=8.0,
                )

    if rag_documents_path.exists():
        for row in iter_jsonl(rag_documents_path):
            canonical_id = str(row.get("canonical_id") or row.get("id") or "").strip()
            if not canonical_id:
                continue
            concept = concepts.setdefault(canonical_id, new_concept(canonical_id))
            concept["entity_types"][str(row.get("content_type") or "unknown")] += 1
            concept["sources"][str(row.get("source") or "unknown")] += 1
            if row.get("category"):
                concept["categories"][str(row["category"])] += 1
            if row.get("content_type"):
                concept["content_types"][str(row["content_type"])] += 1
            add_alias(
                concept,
                name=row.get("title"),
                language=str(row.get("language") or "und"),
                source=str(row.get("source") or "unknown"),
                alias_source="document_title",
                weight=5.0,
            )

    if manual_concepts_path.exists():
        for row in read_json(manual_concepts_path):
            canonical_id = str(row.get("concept_id") or "").strip()
            if not canonical_id:
                continue
            concept = concepts.setdefault(canonical_id, new_concept(canonical_id))
            concept["entity_types"][str(row.get("entity_type") or "manual_concept")] += 100
            concept["sources"]["manual_concepts"] += 100
            for language, names in (row.get("aliases") or {}).items():
                for name in names:
                    add_alias(
                        concept,
                        name=name,
                        language=str(language),
                        source="manual_concepts",
                        alias_source="manual_concepts",
                        weight=20.0,
                    )
            add_alias(
                concept,
                name=row.get("primary_name"),
                language="ko",
                source="manual_concepts",
                alias_source="manual_concepts.primary_name",
                weight=22.0,
            )

    rows = [finalize_concept(concept) for concept in concepts.values()]
    rows = [row for row in rows if row["aliases"]]
    rows.sort(key=lambda row: (row["entity_type"], row["primary_name"] or "", row["concept_id"]))

    alias_count = write_jsonl(out_dir / "entity_aliases.jsonl", rows)
    group_count = write_jsonl(out_dir / "concept_groups.jsonl", concept_group_rows(rows))
    sqlite_report = build_entity_index(out_dir / "entity_index.sqlite3", rows)
    report = {
        "built_at": utc_now(),
        "source_files": {
            "entity_names": str(canonical_entity_path),
            "rag_documents": str(rag_documents_path),
            "manual_concepts": str(manual_concepts_path),
        },
        "outputs": {
            "entity_aliases": str(out_dir / "entity_aliases.jsonl"),
            "concept_groups": str(out_dir / "concept_groups.jsonl"),
            "entity_index": str(out_dir / "entity_index.sqlite3"),
        },
        "concepts": len(rows),
        "alias_rows": sqlite_report["aliases"],
        "entity_alias_records": alias_count,
        "concept_group_records": group_count,
        "sqlite": sqlite_report,
    }
    write_json(out_dir / "entity_alias_report.json", report)
    return report


def new_concept(canonical_id: str) -> dict[str, Any]:
    return {
        "concept_id": canonical_id,
        "canonical_id": canonical_id,
        "aliases_by_key": {},
        "entity_types": Counter(),
        "sources": Counter(),
        "categories": Counter(),
        "content_types": Counter(),
    }


def add_alias(
    concept: dict[str, Any],
    *,
    name: Any,
    language: str,
    source: str,
    alias_source: str,
    weight: float,
) -> None:
    cleaned = clean_alias(name)
    if not cleaned:
        return
    normalized = normalize_alias(cleaned)
    key = (language, normalized)
    existing = concept["aliases_by_key"].get(key)
    if existing is None:
        concept["aliases_by_key"][key] = {
            "language": language,
            "language_label": LANGUAGE_LABELS.get(language, language),
            "name": cleaned,
            "normalized": normalized,
            "source": source,
            "alias_sources": Counter({alias_source: 1}),
            "weight": weight,
        }
        return
    existing["weight"] = max(float(existing["weight"]), weight)
    existing["alias_sources"][alias_source] += 1


def finalize_concept(concept: dict[str, Any]) -> dict[str, Any]:
    aliases = list(concept["aliases_by_key"].values())
    aliases.sort(key=lambda alias: (-float(alias["weight"]), alias["language"], len(alias["name"]), alias["name"]))
    primary_names: dict[str, str] = {}
    for alias in aliases:
        primary_names.setdefault(alias["language"], alias["name"])
    primary_name = primary_names.get("ko") or primary_names.get("en") or next(iter(primary_names.values()), None)
    for alias in aliases:
        alias["alias_sources"] = dict(alias["alias_sources"].most_common())
    entity_type = concept["entity_types"].most_common(1)[0][0] if concept["entity_types"] else "unknown"
    return {
        "concept_id": concept["concept_id"],
        "canonical_id": concept["canonical_id"],
        "entity_type": entity_type,
        "primary_name": primary_name,
        "primary_names": primary_names,
        "aliases": aliases,
        "alias_count": len(aliases),
        "languages": sorted(primary_names),
        "sources": dict(concept["sources"].most_common()),
        "categories": dict(concept["categories"].most_common()),
        "content_types": dict(concept["content_types"].most_common()),
        "confidence": "auto",
    }


def concept_group_rows(rows: list[dict[str, Any]]) -> Iterator[dict[str, Any]]:
    for row in rows:
        yield {
            "concept_id": row["concept_id"],
            "canonical_id": row["canonical_id"],
            "entity_type": row["entity_type"],
            "primary_name": row["primary_name"],
            "primary_names": row["primary_names"],
            "alias_count": row["alias_count"],
            "languages": row["languages"],
            "sources": row["sources"],
            "categories": row["categories"],
            "content_types": row["content_types"],
            "confidence": row["confidence"],
        }


def build_entity_index(db_path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        PRAGMA journal_mode=OFF;
        PRAGMA synchronous=OFF;

        CREATE TABLE concepts (
            concept_id TEXT PRIMARY KEY,
            canonical_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            primary_name TEXT,
            primary_names_json TEXT NOT NULL,
            aliases_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE aliases (
            rowid INTEGER PRIMARY KEY,
            alias_id TEXT UNIQUE NOT NULL,
            concept_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            name TEXT NOT NULL,
            normalized TEXT NOT NULL,
            source TEXT NOT NULL,
            alias_sources_json TEXT NOT NULL,
            weight REAL NOT NULL
        );

        CREATE INDEX idx_aliases_concept_id ON aliases(concept_id);
        CREATE INDEX idx_aliases_language ON aliases(language);
        CREATE INDEX idx_aliases_normalized ON aliases(normalized);
        CREATE INDEX idx_aliases_entity_type ON aliases(entity_type);

        CREATE VIRTUAL TABLE aliases_fts_unicode USING fts5(
            name,
            normalized,
            content='aliases',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE VIRTUAL TABLE aliases_fts_trigram USING fts5(
            name,
            normalized,
            content='aliases',
            content_rowid='rowid',
            tokenize='trigram'
        );
        """
    )
    concept_rows = []
    alias_rows = []
    for row in rows:
        metadata = {
            "sources": row["sources"],
            "categories": row["categories"],
            "content_types": row["content_types"],
            "confidence": row["confidence"],
        }
        concept_rows.append(
            (
                row["concept_id"],
                row["canonical_id"],
                row["entity_type"],
                row["primary_name"],
                stable_json_dumps(row["primary_names"]),
                stable_json_dumps(row["aliases"]),
                stable_json_dumps(metadata),
            )
        )
        for alias in row["aliases"]:
            alias_id = sha256_text(
                stable_json_dumps(
                    {
                        "concept_id": row["concept_id"],
                        "language": alias["language"],
                        "name": alias["name"],
                        "normalized": alias["normalized"],
                    }
                )
            )
            alias_rows.append(
                (
                    alias_id,
                    row["concept_id"],
                    row["canonical_id"],
                    row["entity_type"],
                    alias["language"],
                    alias["language_label"],
                    alias["name"],
                    alias["normalized"],
                    alias["source"],
                    stable_json_dumps(alias["alias_sources"]),
                    alias["weight"],
                )
            )
    conn.executemany(
        """
        INSERT INTO concepts (
            concept_id, canonical_id, entity_type, primary_name,
            primary_names_json, aliases_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        concept_rows,
    )
    conn.executemany(
        """
        INSERT INTO aliases (
            alias_id, concept_id, canonical_id, entity_type, language,
            language_label, name, normalized, source, alias_sources_json, weight
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        alias_rows,
    )
    conn.execute("INSERT INTO aliases_fts_unicode(aliases_fts_unicode) VALUES('rebuild')")
    conn.execute("INSERT INTO aliases_fts_trigram(aliases_fts_trigram) VALUES('rebuild')")
    conn.commit()
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()
    return {
        "db_path": str(db_path),
        "concepts": len(concept_rows),
        "aliases": len(alias_rows),
        "sqlite_integrity_check": integrity,
        "db_size_bytes": db_path.stat().st_size,
    }


def clean_alias(value: Any) -> str | None:
    if value is None:
        return None
    text = clean_text(str(value))
    if not text:
        return None
    if "$UNRELEASED" in text:
        return None
    if text.lower() in {"unknown", "none", "null"}:
        return None
    if len(text) > 140:
        return None
    normalized = normalize_alias(text)
    if len(normalized) < 2:
        return None
    if normalized.isdigit():
        return None
    return text


def normalize_alias(value: str) -> str:
    return "".join(clean_text(value).casefold().split())


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
