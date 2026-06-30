from __future__ import annotations

import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Any

from genshin_lore_db.pipeline.project_amber_v2 import search_project_amber_v2


EVIDENCE_PIN_VERSION = "evidence_pin.v0.1"
SOURCE_LEVELS = {"L0", "L1", "L2", "L3", "L4", "L5"}
EVIDENCE_ROLES = {"supports", "weakly_supports", "context", "counter", "ambiguous", "translation_note"}
WINDOW_ACTIONS = ["expand_before", "expand_after", "read_section", "read_parallel", "pin_evidence"]
SOURCE_RESULT_FIELDS = [
    "result_type",
    "unit_id",
    "chunk_id",
    "document_id",
    "section_id",
    "canonical_id",
    "language",
    "title",
    "text",
    "ordinal",
    "source_url",
    "score",
]


class ProjectAmberV2SourceReader:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path.resolve()
        if not self.db_path.exists():
            raise FileNotFoundError(f"Missing Project Amber v2 search DB: {self.db_path}")
        if self.db_path.is_dir():
            raise IsADirectoryError(f"Expected Project Amber v2 search DB file, got directory: {self.db_path}")

    @classmethod
    def open(cls, root: Path | str = ".") -> "ProjectAmberV2SourceReader":
        root_path = Path(root).resolve()
        if root_path.is_file():
            db_path = root_path
        else:
            db_path = root_path / "data" / "processed" / "search_v2" / "project_amber_search.sqlite3"
        return cls(db_path)

    def find_exact(
        self,
        query: str,
        *,
        language: str | None = None,
        content_type: str | None = None,
        limit: int = 10,
        mode: str = "unicode",
        include_textmap: bool = False,
    ) -> list[dict[str, Any]]:
        rows = search_project_amber_v2(
            self.db_path,
            query,
            language=language,
            content_type=content_type,
            limit=limit,
            mode=mode,
            include_textmap=include_textmap,
        )
        return [normalize_source_result(row) for row in rows]

    def read_unit(self, unit_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM text_units
                WHERE unit_id = ?
                """,
                (unit_id,),
            ).fetchone()
            return decode_row(row) if row else None

    def read_window(self, unit_id: str, *, before: int = 5, after: int = 5) -> dict[str, Any] | None:
        center = self.read_unit(unit_id)
        if center is None:
            return None
        before = max(0, before)
        after = max(0, after)
        document_id = str(center["document_id"])
        ordinal = int(center["ordinal"])
        lower = max(0, ordinal - before)
        upper = ordinal + after
        with self._connect() as conn:
            rows = [
                decode_row(row)
                for row in conn.execute(
                    """
                    SELECT *
                    FROM text_units
                    WHERE document_id = ? AND ordinal BETWEEN ? AND ?
                    ORDER BY ordinal, rowid
                    """,
                    (document_id, lower, upper),
                ).fetchall()
            ]
        return {
            "window_id": f"{unit_id}:window:{before}:{after}",
            "document_id": document_id,
            "canonical_id": center.get("canonical_id"),
            "language": center.get("language"),
            "content_type": center.get("content_type"),
            "title": center.get("title"),
            "document_title": center.get("title"),
            "section_id": center.get("section_id"),
            "source_url": center.get("source_url"),
            "source_level": "L0",
            "next_actions": list(WINDOW_ACTIONS),
            "center_unit_id": unit_id,
            "before": [row for row in rows if int(row["ordinal"]) < ordinal],
            "center": center,
            "after": [row for row in rows if int(row["ordinal"]) > ordinal],
            "units": rows,
        }

    def expand_window(self, window_id: str, *, direction: str, amount: int = 10) -> dict[str, Any] | None:
        unit_id, before, after = parse_window_id(window_id)
        if direction == "before":
            before += validate_positive_int(amount, "amount")
        elif direction == "after":
            after += validate_positive_int(amount, "amount")
        else:
            raise ValueError("direction must be 'before' or 'after'")
        return self.read_window(unit_id, before=before, after=after)

    def read_result_window(self, result: dict[str, Any], *, before: int = 3, after: int = 3) -> dict[str, Any]:
        resolved = self.resolve_result_unit_id(result)
        if not resolved["ok"]:
            return resolved
        unit_id = str(resolved["unit_id"])
        window = self.read_window(unit_id, before=before, after=after)
        if window is None:
            return source_reader_error(
                "source_reader_unit_not_found",
                f"Readable unit was resolved but not found: {unit_id}",
                result=result,
                unit_id=unit_id,
            )
        return {"ok": True, "unit_id": unit_id, "window": window}

    def resolve_result_unit_id(self, result: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_source_result(result)
        unit_id = normalized.get("unit_id") or normalized.get("chunk_id")
        if unit_id:
            return {"ok": True, "unit_id": str(unit_id), "source": "unit_id"}

        document_id = normalized.get("document_id")
        ordinal = normalized.get("ordinal")
        if document_id is None or ordinal is None:
            return source_reader_error(
                "source_reader_mapping_missing",
                "Search result does not include unit_id, chunk_id, or document_id + ordinal.",
                result=normalized,
            )
        try:
            ordinal_int = int(ordinal)
        except (TypeError, ValueError):
            return source_reader_error(
                "source_reader_invalid_ordinal",
                "Search result ordinal is not an integer.",
                result=normalized,
            )

        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT unit_id
                FROM text_units
                WHERE document_id = ? AND ordinal = ?
                ORDER BY rowid
                LIMIT 1
                """,
                (document_id, ordinal_int),
            ).fetchone()
        if row is None:
            return source_reader_error(
                "source_reader_mapping_not_found",
                f"No readable unit exists for document_id={document_id!r} ordinal={ordinal_int}.",
                result=normalized,
            )
        return {"ok": True, "unit_id": str(row["unit_id"]), "source": "document_id_ordinal"}

    def read_section(
        self,
        section_id: str,
        *,
        include_units: bool = True,
        max_units: int | None = None,
    ) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT
                    s.*,
                    d.title AS document_title,
                    d.document_kind AS document_kind,
                    d.source_url AS source_url,
                    d.officialness AS officialness
                FROM sections s
                JOIN documents d ON d.document_id = s.document_id
                WHERE s.section_id = ?
                """,
                (section_id,),
            ).fetchone()
            if row is None:
                return None
            section = decode_row(row)
            unit_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM text_units
                WHERE section_id = ?
                """,
                (section_id,),
            ).fetchone()[0]
            section["unit_count"] = int(unit_count)
            if include_units:
                limit_sql = "" if max_units is None else "LIMIT ?"
                params: tuple[Any, ...] = (section_id,) if max_units is None else (section_id, max_units)
                section["units"] = [
                    decode_row(unit)
                    for unit in conn.execute(
                        f"""
                        SELECT *
                        FROM text_units
                        WHERE section_id = ?
                        ORDER BY ordinal, rowid
                        {limit_sql}
                        """,
                        params,
                    ).fetchall()
                ]
                section["included_unit_count"] = len(section["units"])
            return section

    def read_document(self, document_id: str, *, include_units: bool = True, max_units: int | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM documents
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
            if row is None:
                return None
            document = decode_row(row)
            sections = [
                decode_row(section)
                for section in conn.execute(
                    """
                    SELECT *
                    FROM sections
                    WHERE document_id = ?
                    ORDER BY ordinal, section_id
                    """,
                    (document_id,),
                ).fetchall()
            ]
            document["sections"] = sections
            document["section_count"] = len(sections)
            unit_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM text_units
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()[0]
            document["unit_count"] = int(unit_count)
            if include_units:
                limit_sql = "" if max_units is None else "LIMIT ?"
                params: tuple[Any, ...] = (document_id,) if max_units is None else (document_id, max_units)
                document["units"] = [
                    decode_row(unit)
                    for unit in conn.execute(
                        f"""
                        SELECT *
                        FROM text_units
                        WHERE document_id = ?
                        ORDER BY ordinal, rowid
                        {limit_sql}
                        """,
                        params,
                    ).fetchall()
                ]
                document["included_unit_count"] = len(document["units"])
            return document

    def read_parallel(self, unit_id: str, *, languages: list[str] | None = None) -> dict[str, Any] | None:
        center = self.read_unit(unit_id)
        if center is None:
            return None
        wanted = languages or ["ko", "en", "ja", "zh-Hans"]
        placeholders = ",".join("?" for _ in wanted)
        with self._connect() as conn:
            candidate_rows = [
                decode_row(row)
                for row in conn.execute(
                    f"""
                    SELECT *
                    FROM text_units
                    WHERE canonical_id = ?
                      AND document_kind = ?
                      AND ordinal = ?
                      AND language IN ({placeholders})
                    ORDER BY language, document_id, rowid
                    """,
                    (center["canonical_id"], center["document_kind"], center["ordinal"], *wanted),
                ).fetchall()
            ]
            document_ids = sorted({str(center["document_id"])} | {str(row["document_id"]) for row in candidate_rows})
            doc_placeholders = ",".join("?" for _ in document_ids)
            unit_counts = {
                str(row["document_id"]): int(row["unit_count"])
                for row in conn.execute(
                    f"""
                    SELECT document_id, COUNT(*) AS unit_count
                    FROM text_units
                    WHERE document_id IN ({doc_placeholders})
                    GROUP BY document_id
                    """,
                    tuple(document_ids),
                ).fetchall()
            }
        center_unit_count = unit_counts.get(str(center["document_id"]))
        rows = []
        excluded_languages: dict[str, str] = {}
        for row in candidate_rows:
            language = str(row.get("language") or "")
            if not same_parallel_scope(center, row):
                excluded_languages.setdefault(language, "metadata_scope_mismatch")
                continue
            candidate_unit_count = unit_counts.get(str(row.get("document_id")))
            if candidate_unit_count != center_unit_count:
                excluded_languages.setdefault(language, "unit_count_mismatch")
                continue
            rows.append(row)
        by_language: dict[str, dict[str, Any]] = {}
        for row in rows:
            language = str(row.get("language") or "")
            if language and language not in by_language:
                by_language[language] = row
        blocks = []
        ordered_units = []
        for language in wanted:
            unit = by_language.get(language)
            if unit is None:
                blocks.append(
                    {
                        "language": language,
                        "found": False,
                        "reason": excluded_languages.get(language, "not_found"),
                        "unit": None,
                        "unit_id": None,
                        "text": None,
                    }
                )
                continue
            ordered_units.append(unit)
            blocks.append(
                {
                    "language": language,
                    "found": True,
                    "unit_id": unit.get("unit_id"),
                    "document_id": unit.get("document_id"),
                    "section_id": unit.get("section_id"),
                    "title": unit.get("title"),
                    "ordinal": unit.get("ordinal"),
                    "source_url": unit.get("source_url"),
                    "text": unit.get("text"),
                    "unit": unit,
                }
            )
        return {
            "unit_id": unit_id,
            "canonical_id": center.get("canonical_id"),
            "document_kind": center.get("document_kind"),
            "ordinal": center.get("ordinal"),
            "languages": wanted,
            "alignment": {
                "strategy": "document_kind_ordinal",
                "requires_equal_unit_count": True,
                "center_unit_count": center_unit_count,
            },
            "blocks": blocks,
            "missing_languages": [block["language"] for block in blocks if not block["found"]],
            "units": ordered_units,
        }

    def pin_evidence(
        self,
        document_id: str,
        start_char: int,
        end_char: int,
        *,
        role: str,
        source_level: str = "L0",
        note: str | None = None,
        hypothesis_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        document = self.read_document(document_id, include_units=False)
        if document is None:
            return None
        return build_evidence_pin(
            document_id=document_id,
            canonical_id=document.get("canonical_id"),
            language=document.get("language"),
            content_type=document.get("content_type"),
            title=document.get("title"),
            source_url=document.get("source_url"),
            text=document.get("text") or "",
            start_char=start_char,
            end_char=end_char,
            role=role,
            source_level=source_level,
            note=note,
            hypothesis_ids=hypothesis_ids,
            unit_id=None,
            section_id=None,
        )

    def pin_unit_evidence(
        self,
        unit_id: str,
        start_char: int,
        end_char: int,
        *,
        role: str,
        source_level: str = "L0",
        note: str | None = None,
        hypothesis_ids: list[str] | None = None,
    ) -> dict[str, Any] | None:
        unit = self.read_unit(unit_id)
        if unit is None:
            return None
        return build_evidence_pin(
            document_id=unit.get("document_id"),
            canonical_id=unit.get("canonical_id"),
            language=unit.get("language"),
            content_type=unit.get("content_type"),
            title=unit.get("title"),
            source_url=unit.get("source_url"),
            text=unit.get("text") or "",
            start_char=start_char,
            end_char=end_char,
            role=role,
            source_level=source_level,
            note=note,
            hypothesis_ids=hypothesis_ids,
            unit_id=unit_id,
            section_id=unit.get("section_id"),
        )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn


def decode_row(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    for key in list(data):
        if not key.endswith("_json"):
            continue
        output_key = key.removesuffix("_json")
        try:
            data[output_key] = json.loads(data[key]) if data[key] else None
        except json.JSONDecodeError:
            data[output_key] = None
        del data[key]
    return data


def normalize_source_result(row: dict[str, Any]) -> dict[str, Any]:
    result = dict(row)
    result.setdefault("result_type", "text_unit" if result.get("unit_id") else result.get("result_type"))
    unit_id = result.get("unit_id") or result.get("chunk_id")
    if unit_id:
        result["unit_id"] = str(unit_id)
        result.setdefault("chunk_id", str(unit_id))
    elif "chunk_id" not in result:
        result["chunk_id"] = None
    for field in SOURCE_RESULT_FIELDS:
        result.setdefault(field, None)
    rank = result.get("rank")
    if result.get("score") is None and isinstance(rank, (int, float)):
        result["score"] = round(-float(rank), 6)
    return result


def source_reader_error(
    code: str,
    message: str,
    *,
    result: dict[str, Any] | None = None,
    unit_id: str | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": code, "message": message}
    if unit_id is not None:
        error["unit_id"] = unit_id
    if result is not None:
        error["result"] = {field: result.get(field) for field in SOURCE_RESULT_FIELDS if field in result}
    return {"ok": False, "error": error}


def parse_window_id(window_id: str) -> tuple[str, int, int]:
    try:
        unit_id, bounds = window_id.rsplit(":window:", 1)
        before_text, after_text = bounds.split(":", 1)
        before = int(before_text)
        after = int(after_text)
    except ValueError as exc:
        raise ValueError("window_id must have format '<unit_id>:window:<before>:<after>'") from exc
    if not unit_id:
        raise ValueError("window_id is missing unit_id")
    if before < 0 or after < 0:
        raise ValueError("window_id before/after values must be non-negative")
    return unit_id, before, after


def validate_positive_int(value: int, name: str) -> int:
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def build_evidence_pin(
    *,
    document_id: str | None,
    canonical_id: str | None,
    language: str | None,
    content_type: str | None,
    title: str | None,
    source_url: str | None,
    text: str,
    start_char: int,
    end_char: int,
    role: str,
    source_level: str,
    note: str | None,
    hypothesis_ids: list[str] | None,
    unit_id: str | None,
    section_id: str | None,
) -> dict[str, Any]:
    if role not in EVIDENCE_ROLES:
        raise ValueError(f"role must be one of: {', '.join(sorted(EVIDENCE_ROLES))}")
    if source_level not in SOURCE_LEVELS:
        raise ValueError(f"source_level must be one of: {', '.join(sorted(SOURCE_LEVELS))}")
    if start_char < 0:
        raise ValueError("start_char must be non-negative")
    if end_char <= start_char:
        raise ValueError("end_char must be greater than start_char")
    if end_char > len(text):
        raise ValueError("end_char is outside the source text")

    excerpt = text[start_char:end_char]
    normalized_hypothesis_ids = [str(value) for value in (hypothesis_ids or [])]
    payload = {
        "document_id": document_id,
        "unit_id": unit_id,
        "start_char": start_char,
        "end_char": end_char,
        "role": role,
        "source_level": source_level,
        "excerpt": excerpt,
        "hypothesis_ids": normalized_hypothesis_ids,
    }
    evidence_id = "E-" + hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return {
        "schema_version": EVIDENCE_PIN_VERSION,
        "evidence_id": evidence_id,
        "document_id": document_id,
        "unit_id": unit_id,
        "section_id": section_id,
        "canonical_id": canonical_id,
        "language": language,
        "content_type": content_type,
        "title": title,
        "source_url": source_url,
        "start_char": start_char,
        "end_char": end_char,
        "role": role,
        "source_level": source_level,
        "excerpt": excerpt,
        "hypothesis_ids": normalized_hypothesis_ids,
        "note": note,
    }


def same_parallel_scope(center: dict[str, Any], candidate: dict[str, Any]) -> bool:
    center_metadata = center.get("metadata") or {}
    candidate_metadata = candidate.get("metadata") or {}
    for key in ["kind", "deep_kind", "deep_id", "story_id", "volume_id", "volume_index", "item_id"]:
        center_value = center_metadata.get(key)
        candidate_value = candidate_metadata.get(key)
        if center_value is not None and candidate_value is not None and center_value != candidate_value:
            return False
    return True
