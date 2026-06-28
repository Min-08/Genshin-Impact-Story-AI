from __future__ import annotations

from collections import Counter
from typing import Any

from genshin_lore_db.io import utc_now
from genshin_lore_db.normalize import clean_text


EVIDENCE_PACK_VERSION = "evidence_pack.v0.5"

GROUP_TO_SUPPORT_TYPE = {
    "Direct text units": ("direct", "direct_mentions"),
    "Language variants": ("translation", "translation_variants"),
    "TextMap auxiliary": ("textmap", "textmap_auxiliary"),
    "직접 언급": ("direct", "direct_mentions"),
    "확장 개념 근거": ("expanded", "expanded_concept_evidence"),
    "배경 자료": ("background", "background_sources"),
    "언어별 표현 차이": ("translation", "translation_variants"),
    "TextMap 보조": ("textmap", "textmap_auxiliary"),
    "반박 가능성 후보": ("counter", "counter_evidence_candidates"),
}


def build_evidence_pack(
    *,
    query: str,
    mode: str,
    route: dict[str, Any],
    expansion: dict[str, Any],
    hits: list[dict[str, Any]],
    evidence_groups: list[dict[str, Any]],
    coverage: dict[str, Any],
) -> dict[str, Any]:
    source_rows = build_source_rows(hits, evidence_groups)
    return {
        "schema_version": EVIDENCE_PACK_VERSION,
        "generated_at": utc_now(),
        "query": query,
        "mode": mode,
        "route": route,
        "entities": {
            "seed_concepts": expansion.get("seed_concepts") or [],
            "matched_aliases": expansion.get("matched_aliases") or [],
            "expanded_terms": [
                {
                    "term": term.get("term"),
                    "language": term.get("language"),
                    "source": term.get("source"),
                    "concept_id": term.get("concept_id"),
                    "level": term.get("level"),
                    "weight": term.get("weight"),
                }
                for term in (expansion.get("terms") or [])[:48]
            ],
        },
        "sources": source_rows,
        "groups": build_group_rows(evidence_groups, source_rows),
        "coverage": coverage,
        "quality": quality_summary(hits),
        "limitations": [
            "벡터 검색, 모티프 인덱스, 그래프 검색은 아직 연결되지 않았습니다.",
            "반례는 의미론적 검증이 아니라 부정/대조 표현과 결과 그룹 기반 후보입니다.",
            "Evidence Pack은 LLM 답변 전 단계의 근거 패키지이며, 자체적으로 최종 결론을 생성하지 않습니다.",
        ],
    }


def build_source_rows(hits: list[dict[str, Any]], evidence_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    support_by_result_id: dict[str, str] = {}
    for group in evidence_groups:
        group_name = str(group.get("group") or "")
        support_type = GROUP_TO_SUPPORT_TYPE.get(group_name, ("background", "background_sources"))[0]
        for item in group.get("items") or []:
            if "items" in item and "canonical_id" in item:
                for nested in item.get("items") or []:
                    support_by_result_id.setdefault(result_id(nested), support_type)
            else:
                support_by_result_id.setdefault(result_id(item), support_type)

    rows = []
    seen = set()
    for index, hit in enumerate(hits, start=1):
        rid = result_id(hit)
        if not rid or rid in seen:
            continue
        seen.add(rid)
        excerpt = clean_text(hit.get("excerpt") or hit.get("text") or "")
        rows.append(
            {
                "source_id": f"S{len(rows) + 1}",
                "result_id": rid,
                "chunk_id": hit.get("chunk_id"),
                "unit_id": hit.get("unit_id"),
                "textmap_id": hit.get("textmap_id"),
                "canonical_id": hit.get("canonical_id"),
                "document_id": hit.get("document_id"),
                "support_type": support_by_result_id.get(rid, "background"),
                "title": hit.get("title"),
                "language": hit.get("language"),
                "language_label": hit.get("language_label"),
                "content_type": hit.get("content_type"),
                "category": hit.get("category"),
                "score": hit.get("score"),
                "source_url": hit.get("source_url"),
                "raw_refs": hit.get("raw_refs") or [],
                "matched_terms": hit.get("matched_terms") or [],
                "excerpt": excerpt[:900],
            }
        )
    return rows


def build_group_rows(evidence_groups: list[dict[str, Any]], sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_by_result = {source["result_id"]: source["source_id"] for source in sources}
    rows = []
    for group in evidence_groups:
        label = str(group.get("group") or "")
        support_type, group_id = GROUP_TO_SUPPORT_TYPE.get(label, ("background", label or "unknown"))
        source_ids = []
        for item in group.get("items") or []:
            if "items" in item and "canonical_id" in item:
                for nested in item.get("items") or []:
                    source_id = source_by_result.get(result_id(nested))
                    if source_id and source_id not in source_ids:
                        source_ids.append(source_id)
            else:
                source_id = source_by_result.get(result_id(item))
                if source_id and source_id not in source_ids:
                    source_ids.append(source_id)
        rows.append(
            {
                "group_id": group_id,
                "label": label,
                "support_type": support_type,
                "count": int(group.get("count") or len(source_ids)),
                "source_ids": source_ids,
            }
        )
    return rows


def quality_summary(hits: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(hits)
    if not total:
        return {
            "result_count": 0,
            "unique_canonical_count": 0,
            "source_diversity": 0.0,
            "duplicate_status_rate": 0.0,
            "canonical_repeat_rate": 0.0,
            "low_signal_rate": 0.0,
        }
    canonical_ids = [hit.get("canonical_id") or hit.get("id") for hit in hits]
    canonical_counts = Counter(canonical_ids)
    duplicate_status_count = sum(1 for hit in hits if hit.get("duplicate_status") == "duplicate")
    repeated_canonical_count = sum(max(0, count - 1) for count in canonical_counts.values())
    low_signal_count = sum(1 for hit in hits if not hit.get("matched_terms"))
    return {
        "result_count": total,
        "unique_canonical_count": len(canonical_counts),
        "source_diversity": round(len(canonical_counts) / total, 4),
        "duplicate_status_rate": round(duplicate_status_count / total, 4),
        "canonical_repeat_rate": round(repeated_canonical_count / total, 4),
        "low_signal_rate": round(low_signal_count / total, 4),
        "languages": dict(Counter(hit.get("language") for hit in hits).most_common()),
        "content_types": dict(Counter(hit.get("content_type") for hit in hits).most_common()),
    }


def result_id(item: dict[str, Any]) -> str:
    return str(item.get("id") or item.get("chunk_id") or item.get("unit_id") or item.get("textmap_id") or "")
