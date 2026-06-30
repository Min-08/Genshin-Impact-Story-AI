from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from genshin_lore_db.normalize import clean_text
from genshin_lore_db.pipeline.project_amber_v2 import search_project_amber_v2
from genshin_lore_db.search_engine.evidence import build_evidence_pack, quality_summary
from genshin_lore_db.search_engine.evidence_store import EvidenceStore
from genshin_lore_db.search_engine.router import route_query
from genshin_lore_db.search_engine.source_reader import ProjectAmberV2SourceReader, normalize_source_result


DEFAULT_V2_SEARCH_DB = Path("data") / "processed" / "search_v2" / "project_amber_search.sqlite3"
V2_SEARCH_ENGINE_VERSION = "project_amber_v2_search.v0.1"


class ProjectAmberV2SearchEngine:
    def __init__(self, search_db: Path) -> None:
        self.search_db = search_db.resolve()
        if not self.search_db.exists():
            raise FileNotFoundError(
                f"Missing Project Amber v2 search DB: {self.search_db}. "
                "Run `python scripts/build_project_amber_v2.py` first."
            )
        if self.search_db.is_dir():
            raise IsADirectoryError(f"Expected Project Amber v2 search DB file, got directory: {self.search_db}")

    @classmethod
    def open(cls, root_or_db: Path | str = ".") -> "ProjectAmberV2SearchEngine":
        root_path = Path(root_or_db).resolve()
        if root_path.is_file() or root_path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            return cls(root_path)
        return cls(root_path / DEFAULT_V2_SEARCH_DB)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        language: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        include_textmap: bool = False,
        mode: str = "unicode",
        with_window: bool = False,
        window_before: int = 3,
        window_after: int = 3,
    ) -> dict[str, Any]:
        route = route_query(query).to_dict()
        expansion = build_v2_expansion(query)
        hits = self._search_rows(
            query,
            limit=limit,
            language=language,
            content_type=content_type,
            include_textmap=include_textmap,
            mode=mode,
            expansion=expansion,
        )
        if with_window:
            attach_source_windows(hits, self.search_db, before=window_before, after=window_after)
        result = {
            "query": query,
            "mode": "search",
            "route": route,
            "engine": self.engine_info(),
            "expansion": expansion,
            "results": hits,
            "coverage": v2_coverage_summary(hits),
            "quality": quality_summary(hits),
        }
        add_v2_warnings(result, category=category)
        return result

    def investigate(
        self,
        query: str,
        *,
        limit: int = 40,
        language: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        include_textmap: bool = True,
        mode: str = "unicode",
        workspace_id: str = "default",
    ) -> dict[str, Any]:
        route = route_query(query).to_dict()
        expansion = build_v2_expansion(query)
        hits = self._search_rows(
            query,
            limit=limit,
            language=language,
            content_type=content_type,
            include_textmap=include_textmap,
            mode=mode,
            expansion=expansion,
        )
        evidence_groups = package_v2_evidence(hits)
        coverage = v2_coverage_summary(hits)
        candidate_hits = hits
        if not any(hit.get("unit_id") for hit in candidate_hits):
            candidate_hits = self._search_rows(
                query,
                limit=limit,
                language=language,
                content_type=content_type,
                include_textmap=False,
                mode=mode,
                expansion=expansion,
            )
        candidate_evidence = build_candidate_evidence(candidate_hits, self.search_db, query=query)
        pinned_evidence = load_pinned_evidence(
            self.search_db,
            workspace_id=workspace_id,
            query=query,
            hits=hits,
        )
        evidence_pack = build_evidence_pack(
            query=query,
            mode=route.get("mode") or "investigate",
            route=route,
            expansion=expansion,
            hits=hits,
            evidence_groups=evidence_groups,
            coverage=coverage,
        )
        result = {
            "query": query,
            "mode": "investigate",
            "route": route,
            "engine": self.engine_info(),
            "expansion": expansion,
            "results": hits,
            "evidence_groups": evidence_groups,
            "evidence_pack": evidence_pack,
            "candidate_evidence": candidate_evidence,
            "pinned_evidence": pinned_evidence,
            "counter_candidates": [item for item in candidate_evidence if item.get("suggested_role") == "counter"],
            "translation_note_candidates": [
                item for item in candidate_evidence if item.get("suggested_role") == "translation_note"
            ],
            "evidence_store": {"workspace_id": workspace_id},
            "coverage": coverage,
            "quality": evidence_pack["quality"],
            "llm_ready": {
                "status": "prompt_package_available",
                "supported_future_providers": ["local_llama", "gemini_api"],
                "note": "Project Amber v2 results are packaged for downstream reasoning; no writer is executed here.",
            },
        }
        add_v2_warnings(result, category=category)
        return result

    def engine_info(self) -> dict[str, Any]:
        return {
            "db_version": "v2",
            "search_db": str(self.search_db),
            "search_engine_version": V2_SEARCH_ENGINE_VERSION,
            "retrievers": ["project_amber_v2_fts_unicode", "project_amber_v2_fts_trigram", "textmap_optional"],
        }

    def _search_rows(
        self,
        query: str,
        *,
        limit: int,
        language: str | None,
        content_type: str | None,
        include_textmap: bool,
        mode: str,
        expansion: dict[str, Any],
    ) -> list[dict[str, Any]]:
        rows = search_project_amber_v2(
            self.search_db,
            query,
            language=language,
            content_type=content_type,
            limit=limit,
            mode=mode,
            include_textmap=include_textmap,
        )
        return [normalize_v2_hit(row, expansion=expansion) for row in rows]


def build_v2_expansion(query: str) -> dict[str, Any]:
    terms = []
    for token in [item.strip() for item in clean_text(query).split() if item.strip()]:
        normalized = token.casefold()
        if not normalized:
            continue
        terms.append(
            {
                "term": token,
                "normalized": normalized,
                "language": None,
                "source": "query",
                "concept_id": None,
                "level": 0,
                "weight": 1.0,
            }
        )
    return {"terms": terms, "seed_concepts": [], "matched_aliases": []}


def normalize_v2_hit(row: dict[str, Any], *, expansion: dict[str, Any]) -> dict[str, Any]:
    hit = dict(row)
    rank = hit.get("rank")
    hit["score"] = round(-float(rank), 6) if isinstance(rank, (int, float)) else None
    hit["excerpt"] = v2_excerpt(hit.get("text") or "", expansion)
    hit["matched_terms"] = matched_v2_terms(hit, expansion)
    if hit.get("result_type") == "text_unit":
        hit["category"] = "Project Amber v2"
    elif hit.get("result_type") == "textmap":
        hit["category"] = "TextMap"
    return normalize_source_result(hit)


def attach_source_windows(hits: list[dict[str, Any]], search_db: Path, *, before: int = 3, after: int = 3) -> None:
    reader = ProjectAmberV2SourceReader(search_db)
    for hit in hits:
        resolved = reader.read_result_window(hit, before=before, after=after)
        if resolved["ok"]:
            hit["source_reader"] = {
                "unit_id": resolved["unit_id"],
                "window_id": resolved["window"]["window_id"],
            }
            hit["source_window"] = resolved["window"]
        else:
            hit["source_reader"] = resolved["error"]
            hit["source_window"] = None


def build_candidate_evidence(
    hits: list[dict[str, Any]],
    search_db: Path,
    *,
    query: str,
    limit: int = 12,
) -> list[dict[str, Any]]:
    reader = ProjectAmberV2SourceReader(search_db)
    candidates = []
    seen_units = set()
    for hit in hits:
        unit_id = hit.get("unit_id")
        if not unit_id or unit_id in seen_units:
            continue
        seen_units.add(unit_id)
        window_result = reader.read_result_window(hit, before=1, after=1)
        window = window_result.get("window") if window_result.get("ok") else None
        center = window.get("center") if window else None
        excerpt = clean_text((center or {}).get("text") or hit.get("excerpt") or hit.get("text") or "")
        candidates.append(
            {
                "unit_id": unit_id,
                "document_id": hit.get("document_id"),
                "section_id": hit.get("section_id"),
                "canonical_id": hit.get("canonical_id"),
                "title": hit.get("title"),
                "language": hit.get("language"),
                "content_type": hit.get("content_type"),
                "excerpt": excerpt[:900],
                "suggested_role": suggested_evidence_role(hit, query=query, text=excerpt),
                "score": hit.get("score"),
                "source_url": hit.get("source_url"),
                "window_id": window.get("window_id") if window else None,
                "confirmed": False,
            }
        )
        if len(candidates) >= limit:
            break
    return candidates


def load_pinned_evidence(
    search_db: Path,
    *,
    workspace_id: str,
    query: str,
    hits: list[dict[str, Any]],
    limit: int = 20,
) -> list[dict[str, Any]]:
    store = EvidenceStore.open(search_db, workspace_id=workspace_id)
    records = store.list(query=query)
    seen = {str(record.get("evidence_id")) for record in records}
    hit_unit_ids = {str(hit.get("unit_id")) for hit in hits if hit.get("unit_id")}
    hit_document_ids = {str(hit.get("document_id")) for hit in hits if hit.get("document_id")}
    hit_canonical_ids = {str(hit.get("canonical_id")) for hit in hits if hit.get("canonical_id")}
    for record in store.list():
        evidence_id = str(record.get("evidence_id") or "")
        if evidence_id in seen:
            continue
        if (
            str(record.get("unit_id") or "") in hit_unit_ids
            or str(record.get("document_id") or "") in hit_document_ids
            or str(record.get("canonical_id") or "") in hit_canonical_ids
        ):
            records.append(record)
            seen.add(evidence_id)
        if len(records) >= limit:
            break
    return records[:limit]


def suggested_evidence_role(hit: dict[str, Any], *, query: str, text: str) -> str:
    haystack = clean_text(f"{query}\n{text}\n{hit.get('title') or ''}").casefold()
    if any(term in haystack for term in ["반례", "모순", "counter", "contradict", "however", "but", "아니"]):
        return "counter"
    if any(term in haystack for term in ["번역", "translation", "원문", "일본어", "중국어", "영어"]):
        return "translation_note"
    return "context"


def matched_v2_terms(hit: dict[str, Any], expansion: dict[str, Any]) -> list[dict[str, Any]]:
    text = f"{hit.get('title') or ''}\n{hit.get('speaker') or ''}\n{hit.get('text') or ''}".casefold()
    matched = []
    for term in expansion.get("terms") or []:
        normalized = str(term.get("normalized") or "")
        if normalized and normalized in text:
            matched.append(
                {
                    "term": term.get("term"),
                    "normalized": normalized,
                    "level": term.get("level", 0),
                    "source": term.get("source"),
                    "concept_id": term.get("concept_id"),
                    "channel": "project_amber_v2_fts",
                }
            )
    return matched


def v2_excerpt(text: str, expansion: dict[str, Any], *, max_chars: int = 360) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    lowered = cleaned.casefold()
    for term in expansion.get("terms") or []:
        normalized = str(term.get("normalized") or "")
        if normalized and normalized in lowered:
            center = lowered.index(normalized)
            start = max(0, center - max_chars // 2)
            end = min(len(cleaned), start + max_chars)
            return cleaned[start:end]
    return cleaned[:max_chars]


def v2_coverage_summary(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "results": len(hits),
        "languages": dict(Counter(hit.get("language") for hit in hits).most_common()),
        "categories": dict(Counter(hit.get("category") for hit in hits).most_common()),
        "content_types": dict(Counter(hit.get("content_type") for hit in hits).most_common()),
        "sources": dict(Counter(hit.get("source") for hit in hits).most_common()),
        "document_kinds": dict(Counter(hit.get("document_kind") for hit in hits).most_common()),
    }


def package_v2_evidence(hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    direct_units = [hit for hit in hits if hit.get("result_type") == "text_unit"]
    textmap_hits = [hit for hit in hits if hit.get("result_type") == "textmap"]
    language_variants = []
    by_canonical: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for hit in direct_units:
        canonical_id = hit.get("canonical_id")
        language = hit.get("language")
        if canonical_id and language and language not in by_canonical[canonical_id]:
            by_canonical[str(canonical_id)][str(language)] = hit
    for canonical_id, language_hits in by_canonical.items():
        if len(language_hits) >= 2:
            language_variants.append(
                {
                    "canonical_id": canonical_id,
                    "languages": sorted(language_hits),
                    "items": list(language_hits.values())[:4],
                }
            )
    return [
        {"group": "Direct text units", "count": len(direct_units), "items": direct_units[:12]},
        {"group": "Language variants", "count": len(language_variants), "items": language_variants[:12]},
        {"group": "TextMap auxiliary", "count": len(textmap_hits), "items": textmap_hits[:12]},
    ]


def add_v2_warnings(result: dict[str, Any], *, category: str | None) -> None:
    if not category:
        return
    result["warnings"] = [
        {
            "code": "category_filter_ignored",
            "message": "--category is a v1-only filter and was ignored for Project Amber v2 search.",
            "category": category,
        }
    ]
