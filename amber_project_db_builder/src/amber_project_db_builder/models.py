from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    raw_id: str
    source: str
    source_url: str
    fetched_at: str
    language: str
    raw_format: str
    content_hash: str
    crawler_version: str
    payload: Any
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DocumentRecord:
    doc_id: str
    canonical_group_id: str
    source: str
    source_url: str
    language: str
    content_type: str
    officialness: str
    title: str | None
    text: str
    raw_refs: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ChunkRecord:
    chunk_id: str
    doc_id: str
    canonical_group_id: str
    source: str
    language: str
    content_type: str
    officialness: str
    title: str | None
    ordinal: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EntityNameRecord:
    canonical_id: str
    entity_type: str
    language: str
    name: str
    source: str
    source_doc_id: str | None = None
    aliases: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

