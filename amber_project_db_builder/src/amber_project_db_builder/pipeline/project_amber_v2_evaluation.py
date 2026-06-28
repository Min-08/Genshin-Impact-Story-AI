from __future__ import annotations

from statistics import mean
from typing import Any

from amber_project_db_builder.io import read_json, utc_now
from amber_project_db_builder.pipeline.project_amber_v2 import search_project_amber_v2


def evaluate_project_amber_v2_search(db_path: Any, evaluation_set: dict[str, Any]) -> dict[str, Any]:
    default_limit = int(evaluation_set.get("default_limit") or 10)
    default_mode = str(evaluation_set.get("default_mode") or "unicode")
    cases = [
        evaluate_project_amber_v2_case(db_path, case, default_limit=default_limit, default_mode=default_mode)
        for case in (evaluation_set.get("cases") or [])
    ]
    aggregate = aggregate_metrics(cases)
    thresholds = evaluation_set.get("thresholds") or {}
    return {
        "version": "project_amber_v2_search_eval.v0.1",
        "evaluated_at": utc_now(),
        "db_path": str(db_path),
        "case_count": len(cases),
        "thresholds": thresholds,
        "aggregate": aggregate,
        "passed_thresholds": threshold_results(aggregate, thresholds),
        "cases": cases,
    }


def evaluate_project_amber_v2_case(db_path: Any, case: dict[str, Any], *, default_limit: int, default_mode: str) -> dict[str, Any]:
    query = str(case["query"])
    limit = int(case.get("limit") or default_limit)
    mode = str(case.get("mode") or default_mode)
    hits = search_project_amber_v2(
        db_path,
        query,
        language=case.get("language"),
        content_type=case.get("content_type"),
        limit=limit,
        mode=mode,
        include_textmap=bool(case.get("include_textmap", False)),
    )
    expected_canonical_ids = list(case.get("expected_canonical_ids") or [])
    expected_content_types = list(case.get("expected_content_types") or [])
    expected_languages = list(case.get("expected_languages") or [])
    required_fragments = list(case.get("required_fragments") or [])

    canonical_ids = [hit.get("canonical_id") for hit in hits]
    content_types = {hit.get("content_type") for hit in hits}
    languages = {hit.get("language") for hit in hits}
    combined_text = "\n".join(str(hit.get("title") or "") + "\n" + str(hit.get("text") or "") for hit in hits)

    canonical_hits = [cid for cid in expected_canonical_ids if cid in canonical_ids]
    content_type_hits = [content_type for content_type in expected_content_types if content_type in content_types]
    language_hits = [language for language in expected_languages if language in languages]
    fragment_hits = [fragment for fragment in required_fragments if fragment in combined_text]
    first_rank = first_expected_rank(canonical_ids, expected_canonical_ids)

    metrics = {
        "canonical_recall_at_k": ratio(len(canonical_hits), len(expected_canonical_ids)),
        "content_type_recall": ratio(len(content_type_hits), len(expected_content_types)),
        "language_recall": ratio(len(language_hits), len(expected_languages)),
        "required_fragment_recall": ratio(len(fragment_hits), len(required_fragments)),
        "mrr": 0.0 if first_rank is None else round(1.0 / first_rank, 4),
    }
    return {
        "id": case.get("id"),
        "query": query,
        "mode": mode,
        "limit": limit,
        "expected_canonical_ids": expected_canonical_ids,
        "hit_canonical_ids": canonical_hits,
        "expected_content_types": expected_content_types,
        "hit_content_types": content_type_hits,
        "expected_languages": expected_languages,
        "hit_languages": language_hits,
        "required_fragments": required_fragments,
        "hit_fragments": fragment_hits,
        "top_canonical_ids": canonical_ids[:limit],
        "metrics": metrics,
        "top_results": [
            {
                "rank": index,
                "canonical_id": hit.get("canonical_id"),
                "unit_id": hit.get("unit_id"),
                "document_id": hit.get("document_id"),
                "title": hit.get("title"),
                "language": hit.get("language"),
                "content_type": hit.get("content_type"),
                "document_kind": hit.get("document_kind"),
                "score": hit.get("rank"),
            }
            for index, hit in enumerate(hits[:5], start=1)
        ],
    }


def aggregate_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = [
        "canonical_recall_at_k",
        "content_type_recall",
        "language_recall",
        "required_fragment_recall",
        "mrr",
    ]
    aggregate = {}
    for name in metric_names:
        values = [float(case["metrics"][name]) for case in cases]
        aggregate[name] = round(mean(values), 4) if values else 0.0
    return aggregate


def threshold_results(aggregate: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, bool]:
    return {metric: float(aggregate.get(metric, 0.0)) >= float(threshold) for metric, threshold in thresholds.items()}


def first_expected_rank(canonical_ids: list[str | None], expected: list[str]) -> int | None:
    expected_set = set(expected)
    for index, canonical_id in enumerate(canonical_ids, start=1):
        if canonical_id in expected_set:
            return index
    return None


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 1.0
    return round(numerator / denominator, 4)


def load_project_amber_v2_evaluation_set(path: Any) -> dict[str, Any]:
    return read_json(path)
