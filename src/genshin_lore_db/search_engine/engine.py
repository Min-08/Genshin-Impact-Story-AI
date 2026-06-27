from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from genshin_lore_db.io import ensure_dir, pretty_json_dumps, read_json, sha256_text, stable_json_dumps, write_json
from genshin_lore_db.normalize import clean_text
from genshin_lore_db.search_engine.aliases import LANGUAGE_LABELS, normalize_alias
from genshin_lore_db.search_engine.evidence import build_evidence_pack, quality_summary
from genshin_lore_db.search_engine.router import route_query


DEFAULT_CHANNEL_WEIGHTS = {
    "fts_unicode": 1.0,
    "fts_trigram": 0.82,
    "title_like": 2.3,
    "canonical": 2.0,
    "entity_alias": 1.4,
    "textmap_unicode": 0.42,
    "textmap_trigram": 0.34,
}

DEFAULT_LANGUAGE_WEIGHTS = {
    "ko": 1.28,
    "en": 1.06,
    "ja": 1.0,
    "zh-Hans": 1.0,
    "und": 0.85,
}

DEFAULT_CATEGORY_WEIGHTS = {
    "여행 기록": 1.3,
    "캐릭터": 1.18,
    "아카이브": 1.12,
    "성유물": 1.08,
    "무기": 1.05,
    "업적": 0.98,
    "일곱 성인의 소환": 0.78,
    "가이드북": 0.72,
    "보조 데이터": 0.55,
    "TextMap": 0.46,
}

DEFAULT_CONTENT_WEIGHTS = {
    "quest": 1.32,
    "book": 1.22,
    "avatar": 1.16,
    "reliquary": 1.1,
    "weapon": 1.07,
    "material": 1.04,
    "food": 0.94,
    "achievement": 0.92,
    "monster": 0.88,
    "namecard": 0.86,
    "furniture": 0.78,
    "furnitureSuite": 0.75,
    "gcg": 0.72,
    "everything": 0.54,
    "textmap": 0.46,
}

NEGATION_OR_CONTRAST_TERMS = [
    "아니다",
    "않",
    "그러나",
    "하지만",
    "반면",
    "오히려",
    "not",
    "never",
    "however",
    "but",
    "instead",
    "false",
    "mistaken",
]

QUERY_STOPWORDS = {
    "관련",
    "관계",
    "연결",
    "가능성",
    "근거",
    "정체",
    "추측",
    "설정",
    "자료",
    "조작",
    "효과",
    "모든",
    "전부",
    "대해",
    "대한",
    "알려줘",
    "찾아줘",
    "정리",
    "분석",
}

RELATED_EXPANSION_ENTITY_TYPES = {
    "lore_concept",
    "nation",
    "organization",
    "character_or_entity",
    "manual_concept",
}


@dataclass
class EngineConfig:
    channel_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CHANNEL_WEIGHTS))
    language_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_LANGUAGE_WEIGHTS))
    category_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CATEGORY_WEIGHTS))
    content_weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_CONTENT_WEIGHTS))
    duplicate_weights: dict[str, float] = field(default_factory=lambda: {"unique": 1.0, "representative": 1.05, "duplicate": 0.72})
    max_terms: int = 48
    max_seed_concepts: int = 14
    max_aliases_per_concept: int = 18
    max_related_concepts: int = 12
    per_canonical_limit: int = 2
    vector_backend: str = "none"

    @classmethod
    def from_files(cls, config_path: Path | None, ranking_path: Path | None) -> "EngineConfig":
        config = cls()
        if ranking_path and ranking_path.exists():
            data = read_json(ranking_path)
            config.channel_weights.update(data.get("channel_weights") or {})
            config.language_weights.update(data.get("language_weights") or {})
            config.category_weights.update(data.get("category_weights") or {})
            config.content_weights.update(data.get("content_weights") or {})
            config.duplicate_weights.update(data.get("duplicate_weights") or {})
        if config_path and config_path.exists():
            data = read_json(config_path)
            for field_name in [
                "max_terms",
                "max_seed_concepts",
                "max_aliases_per_concept",
                "max_related_concepts",
                "per_canonical_limit",
                "vector_backend",
            ]:
                if field_name in data:
                    if field_name == "vector_backend":
                        setattr(config, field_name, str(data[field_name]))
                    else:
                        setattr(config, field_name, int(data[field_name]))
        return config

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_terms": self.max_terms,
            "max_seed_concepts": self.max_seed_concepts,
            "max_aliases_per_concept": self.max_aliases_per_concept,
            "max_related_concepts": self.max_related_concepts,
            "per_canonical_limit": self.per_canonical_limit,
            "vector_backend": self.vector_backend,
            "channel_weights": self.channel_weights,
            "language_weights": self.language_weights,
            "category_weights": self.category_weights,
            "content_weights": self.content_weights,
            "duplicate_weights": self.duplicate_weights,
        }


class LoreSearchEngine:
    def __init__(
        self,
        *,
        search_db: Path,
        entity_db: Path,
        config: EngineConfig | None = None,
    ) -> None:
        self.search_db = search_db
        self.entity_db = entity_db
        self.config = config or EngineConfig()
        self.aliases = self._load_aliases()
        self.aliases_by_concept = self._group_aliases()

    @classmethod
    def open(cls, root: Path | str = ".", *, config_dir: Path | None = None) -> "LoreSearchEngine":
        root_path = Path(root).resolve()
        if root_path.is_file():
            search_db = root_path
            project_root = search_db.parents[3]
        else:
            project_root = root_path
            search_db = project_root / "data" / "processed" / "search" / "lore_search.sqlite3"
        entity_db = project_root / "data" / "processed" / "entities" / "entity_index.sqlite3"
        config_root = config_dir or project_root / "data" / "processed" / "search_engine"
        config = EngineConfig.from_files(config_root / "search_config.json", config_root / "ranking_weights.json")
        return cls(search_db=search_db, entity_db=entity_db, config=config)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        language: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        include_textmap: bool = False,
    ) -> dict[str, Any]:
        route = route_query(query).to_dict()
        expansion = self.expand_query(query)
        hits = self._hybrid_retrieve(
            expansion,
            limit=max(limit * 3, 40),
            language=language,
            category=category,
            content_type=content_type,
            include_textmap=include_textmap,
        )
        ranked = self._rank_hits(hits, expansion, limit=limit)
        return {
            "query": query,
            "mode": "search",
            "route": route,
            "engine": self.engine_info(),
            "expansion": expansion,
            "results": ranked,
            "coverage": coverage_summary(ranked),
            "quality": quality_summary(ranked),
        }

    def investigate(
        self,
        query: str,
        *,
        limit: int = 40,
        language: str | None = None,
        category: str | None = None,
        content_type: str | None = None,
        include_textmap: bool = True,
    ) -> dict[str, Any]:
        route = route_query(query).to_dict()
        expansion = self.expand_query(query)
        first_hits = self._rank_hits(
            self._hybrid_retrieve(
                expansion,
                limit=max(limit * 2, 60),
                language=language,
                category=category,
                content_type=content_type,
                include_textmap=False,
            ),
            expansion,
            limit=max(limit, 30),
        )
        related_terms = self.discover_related_terms(first_hits, expansion)
        expansion["terms"].extend(related_terms)
        expansion["related_terms"] = related_terms
        expansion["terms"] = dedupe_terms(expansion["terms"], max_terms=self.config.max_terms)
        hits = self._rank_hits(
            self._hybrid_retrieve(
                expansion,
                limit=max(limit * 4, 120),
                language=language,
                category=category,
                content_type=content_type,
                include_textmap=include_textmap,
            ),
            expansion,
            limit=limit,
        )
        evidence_groups = package_evidence(hits, expansion)
        coverage = coverage_summary(hits)
        evidence_pack = build_evidence_pack(
            query=query,
            mode=route.get("mode") or "investigate",
            route=route,
            expansion=expansion,
            hits=hits,
            evidence_groups=evidence_groups,
            coverage=coverage,
        )
        return {
            "query": query,
            "mode": "investigate",
            "route": route,
            "engine": self.engine_info(),
            "expansion": expansion,
            "results": hits,
            "evidence_groups": evidence_groups,
            "evidence_pack": evidence_pack,
            "coverage": coverage,
            "quality": evidence_pack["quality"],
            "llm_ready": {
                "status": "prompt_package_available",
                "supported_future_providers": ["local_llama", "gemini_api"],
                "note": "현재 엔진은 답변 생성을 하지 않고 근거 패키지만 생성합니다.",
            },
        }

    def expand_query(self, query: str) -> dict[str, Any]:
        normalized_query = normalize_alias(query)
        tokens = query_tokens(query)
        concept_scores: Counter[str] = Counter()
        matched_aliases: list[dict[str, Any]] = []
        for alias in self.aliases:
            alias_norm = alias["normalized"]
            if not alias_norm or len(alias_norm) < 2:
                continue
            if alias_norm in normalized_query:
                score = float(alias["weight"]) + min(len(alias_norm) / 4.0, 8.0)
                concept_scores[alias["concept_id"]] += score
                matched_aliases.append({**alias, "match": "substring", "match_score": score})
        token_norms = {normalize_alias(token) for token in tokens if len(normalize_alias(token)) >= 2}
        for alias in self.aliases:
            if alias["normalized"] in token_norms:
                score = float(alias["weight"]) + 2.0
                concept_scores[alias["concept_id"]] += score
                matched_aliases.append({**alias, "match": "token", "match_score": score})

        seed_concepts = [concept_id for concept_id, _ in concept_scores.most_common(self.config.max_seed_concepts)]
        terms: list[dict[str, Any]] = [
            {
                "term": query,
                "normalized": normalized_query,
                "language": None,
                "level": 0,
                "source": "original_query",
                "concept_id": None,
                "weight": 4.0,
            }
        ]
        for token in tokens:
            terms.append(
                {
                    "term": token,
                    "normalized": normalize_alias(token),
                    "language": None,
                    "level": 0,
                    "source": "query_token",
                    "concept_id": None,
                    "weight": 2.5,
                }
            )
        for concept_id in seed_concepts:
            aliases = sorted(
                self.aliases_by_concept.get(concept_id, []),
                key=lambda alias: (-float(alias["weight"]), language_sort(alias["language"]), len(alias["name"])),
            )
            for alias in aliases[: self.config.max_aliases_per_concept]:
                terms.append(
                    {
                        "term": alias["name"],
                        "normalized": alias["normalized"],
                        "language": alias["language"],
                        "level": 1,
                        "source": "entity_alias",
                        "concept_id": concept_id,
                        "entity_type": alias["entity_type"],
                        "weight": float(alias["weight"]),
                    }
                )

        matched_norms = {alias["normalized"] for alias in matched_aliases}
        parallel_sources = [query] if not seed_concepts else []
        for token in tokens:
            token_norm = normalize_alias(token)
            if token_norm not in matched_norms:
                parallel_sources.append(token)
        for source_query in parallel_sources[:8]:
            terms.extend(self._textmap_parallel_terms(source_query, max_hits=10))

        return {
            "normalized_query": normalized_query,
            "tokens": tokens,
            "seed_concepts": seed_concepts,
            "matched_aliases": compact_aliases(matched_aliases, limit=80),
            "terms": dedupe_terms(terms, max_terms=self.config.max_terms),
        }

    def _textmap_parallel_terms(self, query: str, *, max_hits: int = 16) -> list[dict[str, Any]]:
        if not self.search_db.exists():
            return []
        conn = sqlite3.connect(str(self.search_db))
        conn.row_factory = sqlite3.Row
        ids = []
        for row in conn.execute(
            """
            SELECT t.textmap_id
            FROM textmap_fts_trigram
            JOIN textmap_entries t ON t.rowid = textmap_fts_trigram.rowid
            WHERE textmap_fts_trigram MATCH ?
            ORDER BY bm25(textmap_fts_trigram)
            LIMIT ?
            """,
            (fts_phrase(query), max_hits),
        ):
            ids.append(str(row["textmap_id"]))
        if not ids:
            conn.close()
            return []
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(
            f"""
            SELECT textmap_id, language, text
            FROM textmap_entries
            WHERE textmap_id IN ({placeholders})
            """,
            ids,
        ).fetchall()
        conn.close()
        counts: Counter[tuple[str, str]] = Counter()
        for row in rows:
            for candidate in parallel_text_candidates(row["text"], row["language"]):
                if normalize_alias(candidate) == normalize_alias(query):
                    continue
                counts[(row["language"], candidate)] += 1
        terms = []
        for (language, candidate), count in counts.most_common(24):
            if count < 2:
                continue
            terms.append(
                {
                    "term": candidate,
                    "normalized": normalize_alias(candidate),
                    "language": language,
                    "level": 1,
                    "source": "textmap_parallel_candidate",
                    "concept_id": None,
                    "entity_type": "textmap_parallel_term",
                    "weight": min(3.0 + count, 8.0),
                }
            )
        return terms

    def discover_related_terms(self, hits: list[dict[str, Any]], expansion: dict[str, Any]) -> list[dict[str, Any]]:
        seed_concepts = set(expansion.get("seed_concepts") or [])
        existing = {term["normalized"] for term in expansion.get("terms") or []}
        concept_scores: Counter[str] = Counter()
        top_hits = [hit for hit in hits if hit.get("result_type") == "chunk"][:25]
        for hit in top_hits:
            haystack = normalize_alias(f"{hit.get('title') or ''}\n{hit.get('text') or ''}")
            if not haystack:
                continue
            for alias in self.aliases:
                alias_norm = alias["normalized"]
                if len(alias_norm) < 3 or alias["concept_id"] in seed_concepts or alias_norm in existing:
                    continue
                if not should_use_related_alias(alias):
                    continue
                if alias_norm in haystack:
                    concept_scores[alias["concept_id"]] += float(alias["weight"]) + min(len(alias_norm) / 6.0, 5.0)
        related_terms: list[dict[str, Any]] = []
        for concept_id, score in concept_scores.most_common(self.config.max_related_concepts):
            if score < 12.0:
                continue
            aliases = sorted(
                self.aliases_by_concept.get(concept_id, []),
                key=lambda alias: (-float(alias["weight"]), language_sort(alias["language"]), len(alias["name"])),
            )
            for alias in aliases[: min(8, self.config.max_aliases_per_concept)]:
                related_terms.append(
                    {
                        "term": alias["name"],
                        "normalized": alias["normalized"],
                        "language": alias["language"],
                        "level": 2,
                        "source": "related_entity_from_first_pass",
                        "concept_id": concept_id,
                        "entity_type": alias["entity_type"],
                        "weight": min(float(alias["weight"]), 6.0) + min(score / 20.0, 3.0),
                    }
                )
        return dedupe_terms(related_terms, max_terms=self.config.max_related_concepts * 8)

    def engine_info(self) -> dict[str, Any]:
        return {
            "search_db": str(self.search_db),
            "entity_db": str(self.entity_db),
            "search_engine_version": "0.5.0",
            "alias_count": len(self.aliases),
            "concept_count": len(self.aliases_by_concept),
            "retrievers": [
                "fts_unicode",
                "fts_trigram",
                "title_like",
                "canonical",
                "entity_alias",
                "textmap_optional",
                f"vector:{self.config.vector_backend}",
            ],
        }

    def _load_aliases(self) -> list[dict[str, Any]]:
        if not self.entity_db.exists():
            return []
        conn = sqlite3.connect(str(self.entity_db))
        conn.row_factory = sqlite3.Row
        rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT concept_id, canonical_id, entity_type, language, language_label,
                       name, normalized, source, alias_sources_json, weight
                FROM aliases
                ORDER BY length(normalized) DESC, weight DESC
                """
            )
        ]
        conn.close()
        for row in rows:
            row["alias_sources"] = json.loads(row.pop("alias_sources_json"))
        return rows

    def _group_aliases(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for alias in self.aliases:
            grouped[alias["concept_id"]].append(alias)
        return grouped

    def _hybrid_retrieve(
        self,
        expansion: dict[str, Any],
        *,
        limit: int,
        language: str | None,
        category: str | None,
        content_type: str | None,
        include_textmap: bool,
    ) -> dict[str, dict[str, Any]]:
        conn = sqlite3.connect(str(self.search_db))
        conn.row_factory = sqlite3.Row
        hits: dict[str, dict[str, Any]] = {}
        terms = dedupe_terms(expansion.get("terms") or [], max_terms=self.config.max_terms)
        for term in terms:
            text = term["term"]
            if len(normalize_alias(text)) < 2:
                continue
            self._query_chunk_fts(conn, hits, term, "chunks_fts_unicode", "fts_unicode", limit, language, category, content_type)
            self._query_chunk_fts(conn, hits, term, "chunks_fts_trigram", "fts_trigram", limit, language, category, content_type)
            self._query_title_like(conn, hits, term, limit, language, category, content_type)
            if term.get("concept_id"):
                self._query_canonical(conn, hits, term, limit, language, category, content_type)
            if include_textmap and term.get("level", 0) <= 1:
                self._query_textmap(conn, hits, term, "textmap_fts_unicode", "textmap_unicode", max(10, limit // 4), language)
                self._query_textmap(conn, hits, term, "textmap_fts_trigram", "textmap_trigram", max(10, limit // 4), language)
        conn.close()
        return hits

    def _query_chunk_fts(
        self,
        conn: sqlite3.Connection,
        hits: dict[str, dict[str, Any]],
        term: dict[str, Any],
        table: str,
        channel: str,
        limit: int,
        language: str | None,
        category: str | None,
        content_type: str | None,
    ) -> None:
        filters, params = chunk_filters(language, category, content_type)
        where = f"{table} MATCH ?"
        params = [fts_phrase(term["term"]), *params, limit]
        if filters:
            where += " AND " + " AND ".join(filters)
        sql = f"""
            SELECT c.*, bm25({table}) AS rank
            FROM {table}
            JOIN chunks c ON c.rowid = {table}.rowid
            WHERE {where}
            ORDER BY rank
            LIMIT ?
        """
        for row in conn.execute(sql, params):
            score = max(0.1, min(-float(row["rank"]), 25.0))
            self._add_chunk_hit(hits, row, channel, score, term)

    def _query_title_like(
        self,
        conn: sqlite3.Connection,
        hits: dict[str, dict[str, Any]],
        term: dict[str, Any],
        limit: int,
        language: str | None,
        category: str | None,
        content_type: str | None,
    ) -> None:
        filters, params = chunk_filters(language, category, content_type)
        like = f"%{term['term']}%"
        where = "c.title LIKE ?"
        params = [like, *params, limit]
        if filters:
            where += " AND " + " AND ".join(filters)
        sql = f"SELECT c.*, 0.0 AS rank FROM chunks c WHERE {where} LIMIT ?"
        for row in conn.execute(sql, params):
            score = 7.0 if normalize_alias(row["title"] or "") == term["normalized"] else 4.0
            self._add_chunk_hit(hits, row, "title_like", score, term)

    def _query_canonical(
        self,
        conn: sqlite3.Connection,
        hits: dict[str, dict[str, Any]],
        term: dict[str, Any],
        limit: int,
        language: str | None,
        category: str | None,
        content_type: str | None,
    ) -> None:
        filters, params = chunk_filters(language, category, content_type)
        where = "c.canonical_id = ?"
        params = [term["concept_id"], *params, min(limit, 50)]
        if filters:
            where += " AND " + " AND ".join(filters)
        sql = f"SELECT c.*, 0.0 AS rank FROM chunks c WHERE {where} ORDER BY c.language = 'ko' DESC, c.ordinal LIMIT ?"
        for row in conn.execute(sql, params):
            self._add_chunk_hit(hits, row, "canonical", 5.5, term)

    def _query_textmap(
        self,
        conn: sqlite3.Connection,
        hits: dict[str, dict[str, Any]],
        term: dict[str, Any],
        table: str,
        channel: str,
        limit: int,
        language: str | None,
    ) -> None:
        filters = []
        params: list[Any] = [fts_phrase(term["term"])]
        if language:
            filters.append("t.language = ?")
            params.append(language)
        where = f"{table} MATCH ?"
        if filters:
            where += " AND " + " AND ".join(filters)
        params.append(limit)
        sql = f"""
            SELECT t.*, bm25({table}) AS rank
            FROM {table}
            JOIN textmap_entries t ON t.rowid = {table}.rowid
            WHERE {where}
            ORDER BY rank
            LIMIT ?
        """
        for row in conn.execute(sql, params):
            score = max(0.1, min(-float(row["rank"]), 18.0))
            self._add_textmap_hit(hits, row, channel, score, term)

    def _add_chunk_hit(
        self,
        hits: dict[str, dict[str, Any]],
        row: sqlite3.Row,
        channel: str,
        score: float,
        term: dict[str, Any],
    ) -> None:
        key = f"chunk:{row['chunk_id']}"
        hit = hits.get(key)
        if hit is None:
            hit = {
                "result_type": "chunk",
                "id": row["chunk_id"],
                "chunk_id": row["chunk_id"],
                "document_id": row["document_id"],
                "canonical_id": row["canonical_id"],
                "source": row["source"],
                "source_label": row["source_label"],
                "language": row["language"],
                "language_label": row["language_label"],
                "category": row["category"],
                "subcategory": row["subcategory"],
                "content_type": row["content_type"],
                "officialness": row["officialness"],
                "title": row["title"],
                "ordinal": row["ordinal"],
                "text": row["text"],
                "duplicate_status": row["duplicate_status"],
                "duplicate_of": row["duplicate_of"],
                "source_url": row["source_url"],
                "raw_refs": safe_json_loads(row["raw_refs_json"], []),
                "metadata": safe_json_loads(row["metadata_json"], {}),
                "channels": {},
                "matched_terms": [],
            }
            hits[key] = hit
        self._add_channel(hit, channel, score, term)

    def _add_textmap_hit(
        self,
        hits: dict[str, dict[str, Any]],
        row: sqlite3.Row,
        channel: str,
        score: float,
        term: dict[str, Any],
    ) -> None:
        key = f"textmap:{row['textmap_id']}:{row['language']}"
        hit = hits.get(key)
        if hit is None:
            hit = {
                "result_type": "textmap",
                "id": row["textmap_id"],
                "textmap_id": row["textmap_id"],
                "document_id": None,
                "canonical_id": f"textmap:{row['textmap_id']}",
                "source": row["source"],
                "source_label": row["source_label"],
                "language": row["language"],
                "language_label": row["language_label"],
                "category": "TextMap",
                "subcategory": None,
                "content_type": "textmap",
                "officialness": "official_text",
                "title": row["textmap_id"],
                "ordinal": 0,
                "text": row["text"],
                "duplicate_status": "unique",
                "duplicate_of": None,
                "source_url": row["source_url"],
                "raw_refs": [row["raw_ref"]] if row["raw_ref"] else [],
                "metadata": {"content_hash": row["content_hash"]},
                "channels": {},
                "matched_terms": [],
            }
            hits[key] = hit
        self._add_channel(hit, channel, score, term)

    def _add_channel(self, hit: dict[str, Any], channel: str, score: float, term: dict[str, Any]) -> None:
        hit["channels"][channel] = hit["channels"].get(channel, 0.0) + score
        term_ref = {
            "term": term["term"],
            "normalized": term["normalized"],
            "level": term.get("level", 0),
            "source": term.get("source"),
            "concept_id": term.get("concept_id"),
            "channel": channel,
        }
        if term_ref not in hit["matched_terms"]:
            hit["matched_terms"].append(term_ref)

    def _rank_hits(self, hits: dict[str, dict[str, Any]], expansion: dict[str, Any], *, limit: int) -> list[dict[str, Any]]:
        ranked = []
        for hit in hits.values():
            score = self._score_hit(hit, expansion)
            hit["score"] = round(score, 6)
            hit["score_breakdown"] = score_breakdown(hit, self.config)
            hit["excerpt"] = excerpt_text(hit["text"], expansion)
            ranked.append(hit)
        ranked.sort(key=lambda item: item["score"], reverse=True)
        ranked = seed_concept_priority_rows(ranked, expansion)
        return cap_per_canonical(ranked, limit=limit, per_canonical_limit=self.config.per_canonical_limit)

    def _score_hit(self, hit: dict[str, Any], expansion: dict[str, Any]) -> float:
        score = 0.0
        for channel, raw_score in hit["channels"].items():
            score += raw_score * self.config.channel_weights.get(channel, 1.0)
        score *= self.config.language_weights.get(hit.get("language"), 1.0)
        score *= self.config.category_weights.get(hit.get("category"), 1.0)
        score *= self.config.content_weights.get(hit.get("content_type"), 1.0)
        score *= self.config.duplicate_weights.get(hit.get("duplicate_status"), 1.0)
        title_norm = normalize_alias(hit.get("title") or "")
        text_norm = normalize_alias(hit.get("text") or "")
        for term in expansion.get("terms") or []:
            term_norm = term.get("normalized")
            if not term_norm:
                continue
            if title_norm == term_norm:
                score += 6.0
            elif term_norm and term_norm in title_norm:
                score += 2.4
            if term_norm and term_norm in text_norm:
                score += 0.65 + min(float(term.get("weight") or 1.0) / 20.0, 0.6)
        if len(hit.get("text") or "") < 80:
            score *= 0.72
        return score


def write_search_engine_assets(root: Path) -> dict[str, Any]:
    root = root.resolve()
    out_dir = root / "data" / "processed" / "search_engine"
    ensure_dir(out_dir)
    config = EngineConfig()
    search_config = {
        "search_engine_version": "0.5.0",
        "evidence_pack_schema": "evidence_pack.v0.5",
        "max_terms": config.max_terms,
        "max_seed_concepts": config.max_seed_concepts,
        "max_aliases_per_concept": config.max_aliases_per_concept,
        "max_related_concepts": config.max_related_concepts,
        "per_canonical_limit": config.per_canonical_limit,
        "vector_backend": config.vector_backend,
        "retrieval_order": ["fts_unicode", "fts_trigram", "title_like", "canonical", "entity_alias", "textmap_optional"],
        "llm_connectors_planned": ["local_llama", "gemini_api"],
        "developer_tools": ["route", "search", "investigate", "eval_search_engine"],
    }
    ranking_weights = {
        "channel_weights": config.channel_weights,
        "language_weights": config.language_weights,
        "category_weights": config.category_weights,
        "content_weights": config.content_weights,
        "duplicate_weights": config.duplicate_weights,
    }
    write_json(out_dir / "search_config.json", search_config)
    write_json(out_dir / "ranking_weights.json", ranking_weights)
    report = {
        "built_at": utc_now(),
        "purpose": "developer_core_search_engine_v0.5",
        "outputs": {
            "search_config": str(out_dir / "search_config.json"),
            "ranking_weights": str(out_dir / "ranking_weights.json"),
        },
        "notes": [
            "웹 UI 없이 CLI/Python API로 쓰는 검색 엔진 코어입니다.",
            "LLM 연결은 현재 프롬프트 패키지 생성까지만 담당하고, 실제 API 호출은 추후 커넥터에서 붙입니다.",
        ],
    }
    write_json(out_dir / "engine_report.json", report)
    return report


def chunk_filters(language: str | None, category: str | None, content_type: str | None) -> tuple[list[str], list[Any]]:
    filters = []
    params: list[Any] = []
    if language:
        filters.append("c.language = ?")
        params.append(language)
    if category:
        filters.append("c.category = ?")
        params.append(category)
    if content_type:
        filters.append("c.content_type = ?")
        params.append(content_type)
    return filters, params


def fts_phrase(value: str) -> str:
    text = clean_text(value)
    if not text:
        return '""'
    return f'"{text.replace(chr(34), chr(34) + chr(34))}"'


def query_tokens(query: str) -> list[str]:
    rough = []
    for token in clean_text(query).replace("/", " ").replace(",", " ").split():
        token = token.strip("()[]{}<>\"'`.,;:!?")
        candidates = normalize_korean_candidates(token) if re.search(r"[가-힣]", token) else [token]
        for candidate in candidates:
            normalized = normalize_alias(candidate)
            if len(normalized) >= 2 and normalized not in QUERY_STOPWORDS:
                rough.append(candidate)
    return rough[:24]


def parallel_text_candidates(text: str, language: str) -> list[str]:
    cleaned = clean_text(text)
    if language == "ko":
        tokens = re.split(r"[^0-9A-Za-z가-힣']+", cleaned)
        return [candidate for token in tokens for candidate in normalize_korean_candidates(token)]
    if language == "ja":
        tokens = re.split(r"[^0-9A-Za-zァ-ヶー一-龯']+", cleaned)
        return [candidate for token in tokens for candidate in normalize_japanese_candidates(token)]
    if language == "en":
        tokens = re.findall(r"[A-Z][A-Za-z'’-]{2,}(?:\s+[A-Z][A-Za-z'’-]{2,})?", cleaned)
        return [token for token in tokens if valid_candidate(token)]
    if language == "zh-Hans":
        # Chinese text has no reliable word boundaries here. Keep only short quoted/name-like spans.
        tokens = re.findall(r"[「《]([^」》]{2,12})[」》]", cleaned)
        return [token for token in tokens if valid_candidate(token)]
    return []


def normalize_korean_candidates(token: str) -> list[str]:
    token = token.strip()
    if not token:
        return []
    suffixes = [
        "으로부터",
        "으로서",
        "에서는",
        "에게서",
        "까지",
        "부터",
        "에게",
        "에서",
        "으로",
        "라고",
        "이랑",
        "와",
        "과",
        "의",
        "은",
        "는",
        "이",
        "가",
        "을",
        "를",
        "에",
        "로",
        "도",
        "만",
    ]
    candidates = [token]
    current = token
    for _ in range(3):
        changed = False
        for suffix in suffixes:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                current = current[: -len(suffix)]
                candidates.append(current)
                changed = True
                break
        if not changed:
            break
    valid = [candidate for candidate in candidates if valid_candidate(candidate)]
    if len(valid) > 1:
        return [valid[-1]]
    return valid


def normalize_japanese_candidates(token: str) -> list[str]:
    token = token.strip()
    if not token:
        return []
    suffixes = ["について", "から", "まで", "には", "では", "とは", "が", "を", "に", "へ", "の", "は", "も", "で", "と"]
    candidates = [token]
    current = token
    for _ in range(3):
        changed = False
        for suffix in suffixes:
            if current.endswith(suffix) and len(current) > len(suffix) + 1:
                current = current[: -len(suffix)]
                candidates.append(current)
                changed = True
                break
        if not changed:
            break
    valid = [candidate for candidate in candidates if valid_candidate(candidate)]
    if len(valid) > 1:
        return [valid[-1]]
    return valid


def valid_candidate(value: str) -> bool:
    normalized = normalize_alias(value)
    if len(normalized) < 2 or len(normalized) > 30:
        return False
    if normalized.isdigit():
        return False
    stopwords = {
        "the",
        "and",
        "that",
        "this",
        "with",
        "from",
        "traveler",
        "paimon",
        "솔직히",
        "기억",
        "정보",
        "정도",
        "자신",
        "우리",
        "너희",
        "시간",
        "역시",
        "거야",
        "맞아",
        "정말",
        "그럼",
        "이제",
        "아무튼",
        "좋다",
    }
    return normalized not in stopwords


def should_use_related_alias(alias: dict[str, Any]) -> bool:
    concept_id = str(alias.get("concept_id") or "")
    if concept_id.startswith("manual:"):
        return True
    entity_type = str(alias.get("entity_type") or "")
    return entity_type in RELATED_EXPANSION_ENTITY_TYPES


def dedupe_terms(terms: Iterable[dict[str, Any]], *, max_terms: int) -> list[dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    for term in terms:
        normalized = term.get("normalized") or normalize_alias(term.get("term") or "")
        if len(normalized) < 2:
            continue
        row = {**term, "normalized": normalized}
        previous = best.get(normalized)
        if previous is None or (row.get("weight") or 0) > (previous.get("weight") or 0):
            best[normalized] = row
    rows = list(best.values())
    rows.sort(key=lambda row: (int(row.get("level") or 0), -float(row.get("weight") or 0), len(row.get("term") or "")))
    return rows[:max_terms]


def compact_aliases(aliases: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    seen = set()
    rows = []
    aliases.sort(key=lambda alias: (-float(alias.get("match_score") or 0), -len(alias.get("normalized") or "")))
    for alias in aliases:
        key = (alias["concept_id"], alias["language"], alias["normalized"])
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "concept_id": alias["concept_id"],
                "entity_type": alias["entity_type"],
                "language": alias["language"],
                "name": alias["name"],
                "match": alias["match"],
                "match_score": round(float(alias["match_score"]), 3),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def language_sort(language: str) -> int:
    return {"ko": 0, "en": 1, "ja": 2, "zh-Hans": 3, "und": 4}.get(language, 9)


def safe_json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except Exception:  # noqa: BLE001
        return fallback


def score_breakdown(hit: dict[str, Any], config: EngineConfig) -> dict[str, Any]:
    return {
        "channels": {channel: round(score, 4) for channel, score in sorted(hit["channels"].items())},
        "language_weight": config.language_weights.get(hit.get("language"), 1.0),
        "category_weight": config.category_weights.get(hit.get("category"), 1.0),
        "content_weight": config.content_weights.get(hit.get("content_type"), 1.0),
        "duplicate_weight": config.duplicate_weights.get(hit.get("duplicate_status"), 1.0),
    }


def excerpt_text(text: str, expansion: dict[str, Any], *, radius: int = 260) -> str:
    cleaned = clean_text(text)
    normalized = normalize_alias(cleaned)
    best_index = -1
    for term in expansion.get("terms") or []:
        term_norm = term.get("normalized")
        if term_norm and term_norm in normalized:
            best_index = normalized.find(term_norm)
            break
    if best_index < 0:
        return cleaned[: radius * 2].strip()
    # The normalized index is approximate for CJK/whitespace. A compact prefix is still useful.
    return cleaned[: radius * 2].strip()


def cap_per_canonical(rows: list[dict[str, Any]], *, limit: int, per_canonical_limit: int) -> list[dict[str, Any]]:
    result = []
    counts: Counter[str] = Counter()
    for row in rows:
        canonical_id = row.get("canonical_id") or row.get("id")
        if row.get("result_type") == "chunk" and counts[canonical_id] >= per_canonical_limit:
            continue
        counts[canonical_id] += 1
        result.append(compact_hit(row))
        if len(result) >= limit:
            break
    return result


def seed_concept_priority_rows(rows: list[dict[str, Any]], expansion: dict[str, Any]) -> list[dict[str, Any]]:
    seed_concepts = [concept_id for concept_id in expansion.get("seed_concepts") or [] if concept_id]
    priority = []
    seen_ids = set()
    for concept_id in seed_concepts:
        for row in rows:
            matched = {term.get("concept_id") for term in row.get("matched_terms") or []}
            if concept_id in matched and row.get("id") not in seen_ids:
                priority.append(row)
                seen_ids.add(row.get("id"))
                break
    return priority + [row for row in rows if row.get("id") not in seen_ids]


def compact_hit(row: dict[str, Any]) -> dict[str, Any]:
    keep = [
        "result_type",
        "id",
        "chunk_id",
        "textmap_id",
        "document_id",
        "canonical_id",
        "source",
        "source_label",
        "language",
        "language_label",
        "category",
        "subcategory",
        "content_type",
        "title",
        "ordinal",
        "text",
        "excerpt",
        "score",
        "score_breakdown",
        "duplicate_status",
        "duplicate_of",
        "source_url",
        "raw_refs",
        "metadata",
        "matched_terms",
        "channels",
    ]
    return {key: row.get(key) for key in keep if key in row}


def coverage_summary(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "results": len(hits),
        "languages": dict(Counter(hit.get("language") for hit in hits).most_common()),
        "categories": dict(Counter(hit.get("category") for hit in hits).most_common()),
        "content_types": dict(Counter(hit.get("content_type") for hit in hits).most_common()),
        "sources": dict(Counter(hit.get("source") for hit in hits).most_common()),
    }


def package_evidence(hits: list[dict[str, Any]], expansion: dict[str, Any]) -> list[dict[str, Any]]:
    groups = {
        "직접 언급": [],
        "확장 개념 근거": [],
        "배경 자료": [],
        "언어별 표현 차이": [],
        "TextMap 보조": [],
        "반박 가능성 후보": [],
    }
    original_norms = {term["normalized"] for term in expansion.get("terms") or [] if term.get("level") in {0, 1}}
    for hit in hits:
        if hit.get("result_type") == "textmap":
            groups["TextMap 보조"].append(hit)
            continue
        text_norm = normalize_alias(f"{hit.get('title') or ''}\n{hit.get('text') or ''}")
        levels = {term.get("level") for term in hit.get("matched_terms") or []}
        if any(term_norm and term_norm in text_norm for term_norm in original_norms):
            groups["직접 언급"].append(hit)
        elif 2 in levels:
            groups["확장 개념 근거"].append(hit)
        elif hit.get("category") == "아카이브" or hit.get("content_type") in {"book", "reliquary", "weapon", "material"}:
            groups["배경 자료"].append(hit)
        if any(term in clean_text(hit.get("text") or "").casefold() for term in NEGATION_OR_CONTRAST_TERMS):
            groups["반박 가능성 후보"].append(hit)

    by_canonical: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for hit in hits:
        if hit.get("result_type") != "chunk":
            continue
        canonical_id = hit.get("canonical_id")
        language = hit.get("language")
        if canonical_id and language and language not in by_canonical[canonical_id]:
            by_canonical[canonical_id][language] = hit
    for canonical_id, language_hits in by_canonical.items():
        if len(language_hits) >= 2:
            groups["언어별 표현 차이"].append(
                {
                    "canonical_id": canonical_id,
                    "languages": sorted(language_hits),
                    "items": list(language_hits.values())[:4],
                }
            )

    output = []
    for name, items in groups.items():
        output.append(
            {
                "group": name,
                "count": len(items),
                "items": items[:12],
            }
        )
    return output


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
