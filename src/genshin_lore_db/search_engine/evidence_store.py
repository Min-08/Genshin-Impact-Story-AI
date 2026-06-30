from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from genshin_lore_db.io import ensure_dir, stable_json_dumps, utc_now
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.search_engine.source_reader import EVIDENCE_PIN_VERSION


DEFAULT_WORKSPACE_ID = "default"
EVIDENCE_STORE_FILENAME = "evidence_pins.jsonl"
DB_SUFFIXES = {".db", ".sqlite", ".sqlite3"}
WORKSPACE_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class EvidenceStore:
    root: Path
    workspace_id: str = DEFAULT_WORKSPACE_ID

    @classmethod
    def open(cls, root_or_db: Path | str = ".", *, workspace_id: str = DEFAULT_WORKSPACE_ID) -> "EvidenceStore":
        workspace = validate_workspace_id(workspace_id)
        return cls(workspace_project_root(root_or_db), workspace)

    @property
    def path(self) -> Path:
        return self.root / "data" / "workspaces" / self.workspace_id / EVIDENCE_STORE_FILENAME

    def append(self, evidence: dict[str, Any], *, created_at: str | None = None) -> dict[str, Any]:
        record = normalize_evidence_record(evidence, workspace_id=self.workspace_id, created_at=created_at)
        existing = self.get(str(record["evidence_id"]))
        if existing is not None:
            return {"created": False, "record": existing, "path": str(self.path)}

        ensure_dir(self.path.parent)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(stable_json_dumps(record) + "\n")
        return {"created": True, "record": record, "path": str(self.path)}

    def list(self, *, role: str | None = None, query: str | None = None) -> list[dict[str, Any]]:
        rows = [row for row in self._read_rows() if row.get("workspace_id") == self.workspace_id]
        if role:
            rows = [row for row in rows if row.get("role") == role]
        if query:
            needle = normalize_query(query)
            rows = [row for row in rows if evidence_matches_query(row, needle)]
        return rows

    def get(self, evidence_id: str) -> dict[str, Any] | None:
        for row in self._read_rows():
            if row.get("workspace_id") == self.workspace_id and row.get("evidence_id") == evidence_id:
                return row
        return None

    def _read_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
        return rows


def normalize_evidence_record(
    evidence: dict[str, Any],
    *,
    workspace_id: str,
    created_at: str | None = None,
) -> dict[str, Any]:
    workspace = validate_workspace_id(workspace_id)
    evidence_id = str(evidence.get("evidence_id") or "")
    if not evidence_id:
        raise ValueError("evidence record is missing evidence_id")
    record = dict(evidence)
    record["schema_version"] = record.get("schema_version") or EVIDENCE_PIN_VERSION
    record["workspace_id"] = workspace
    record["hypothesis_ids"] = [str(value) for value in (record.get("hypothesis_ids") or [])]
    record["created_at"] = record.get("created_at") or created_at or utc_now()
    for key in [
        "document_id",
        "unit_id",
        "section_id",
        "canonical_id",
        "language",
        "content_type",
        "title",
        "source_url",
        "role",
        "source_level",
        "excerpt",
        "note",
    ]:
        record.setdefault(key, None)
    return record


def validate_workspace_id(workspace_id: str) -> str:
    workspace = str(workspace_id or "").strip()
    if not workspace:
        raise ValueError("workspace_id is required")
    if not WORKSPACE_ID_PATTERN.fullmatch(workspace):
        raise ValueError("workspace_id may contain only letters, numbers, underscores, and hyphens")
    return workspace


def workspace_project_root(root_or_db: Path | str) -> Path:
    root_path = Path(root_or_db).resolve()
    if root_path.is_file() or root_path.suffix.lower() in DB_SUFFIXES:
        if (
            root_path.parent.name == "search_v2"
            and root_path.parent.parent.name == "processed"
            and root_path.parent.parent.parent.name == "data"
        ):
            return root_path.parent.parent.parent.parent
        return root_path.parent
    return root_path


def normalize_query(query: str) -> str:
    return clean_text(query).casefold()


def evidence_matches_query(record: dict[str, Any], needle: str) -> bool:
    if not needle:
        return True
    haystack = "\n".join(
        str(record.get(key) or "")
        for key in [
            "evidence_id",
            "document_id",
            "unit_id",
            "section_id",
            "canonical_id",
            "title",
            "excerpt",
            "note",
            "language",
            "content_type",
        ]
    )
    return needle in clean_text(haystack).casefold()
