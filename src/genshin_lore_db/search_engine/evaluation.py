from __future__ import annotations

from statistics import mean
from typing import Any

from genshin_lore_db.io import read_json, utc_now
from genshin_lore_db.search_engine.evidence import quality_summary
from genshin_lore_db.search_engine.router import route_query


def evaluate_search_engine(engine: Any, evaluation_set: dict[str, Any]) -> dict[str, Any]:
    default_limit = int(evaluation_set.get("default_limit") or 10)
    cases = []
    for case in evaluation_set.get("cases") or []:
        cases.append(evaluate_case(engine, case, default_limit=default_limit))
    aggregate = aggregate_metrics(cases)
    thresholds = evaluation_set.get("thresholds") or {}
    return {
        "version": "0.5.0",
        "evaluated_at": utc_now(),
        "case_count": len(cases),
        "thresholds": thresholds,
        "aggregate": aggregate,
        "passed_thresholds": threshold_results(aggregate, thresholds),
        "cases": cases,
    }


def evaluate_case(engine: Any, case: dict[str, Any], *, default_limit: int) -> dict[str, Any]:
    query = str(case["query"])
    limit = int(case.get("limit") or default_limit)
    route = route_query(query).to_dict()
    result = engine.search(query, limit=limit, include_textmap=bool(case.get("include_textmap", False)))
    hits = result.get("results") or []
    canonical_ids = [hit.get("canonical_id") for hit in hits]
    content_types = {hit.get("content_type") for hit in hits}
    seed_concepts = set(result.get("expansion", {}).get("seed_concepts") or [])

    expected_canonical_ids = list(case.get("expected_canonical_ids") or [])
    expected_concepts = list(case.get("expected_concepts") or [])
    expected_content_types = list(case.get("expected_content_types") or [])
    expected_route = case.get("expected_route")

    canonical_hits = [cid for cid in expected_canonical_ids if cid in canonical_ids]
    concept_hits = [concept for concept in expected_concepts if concept in seed_concepts]
    content_type_hits = [content_type for content_type in expected_content_types if content_type in content_types]
    first_rank = first_expected_rank(canonical_ids, expected_canonical_ids)
    metrics = {
        "canonical_recall_at_k": ratio(len(canonical_hits), len(expected_canonical_ids)),
        "concept_recall": ratio(len(concept_hits), len(expected_concepts)),
        "content_type_recall": ratio(len(content_type_hits), len(expected_content_types)),
        "mrr": 0.0 if first_rank is None else round(1.0 / first_rank, 4),
        "route_match": 1.0 if not expected_route or route["mode"] == expected_route else 0.0,
    }
    return {
        "id": case.get("id"),
        "query": query,
        "expected_route": expected_route,
        "route": route,
        "expected_canonical_ids": expected_canonical_ids,
        "hit_canonical_ids": canonical_hits,
        "top_canonical_ids": canonical_ids[:limit],
        "expected_concepts": expected_concepts,
        "hit_concepts": concept_hits,
        "seed_concepts": sorted(seed_concepts),
        "expected_content_types": expected_content_types,
        "hit_content_types": content_type_hits,
        "metrics": metrics,
        "quality": quality_summary(hits),
        "top_results": [
            {
                "rank": index,
                "canonical_id": hit.get("canonical_id"),
                "title": hit.get("title"),
                "language": hit.get("language"),
                "content_type": hit.get("content_type"),
                "score": hit.get("score"),
            }
            for index, hit in enumerate(hits[:5], start=1)
        ],
    }


def aggregate_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    metric_names = ["canonical_recall_at_k", "concept_recall", "content_type_recall", "mrr", "route_match"]
    aggregate = {}
    for name in metric_names:
        values = [float(case["metrics"][name]) for case in cases]
        aggregate[name] = round(mean(values), 4) if values else 0.0
    aggregate["route_accuracy"] = aggregate.pop("route_match")
    aggregate["mean_duplicate_status_rate"] = round(mean([case["quality"]["duplicate_status_rate"] for case in cases]), 4) if cases else 0.0
    aggregate["mean_canonical_repeat_rate"] = round(mean([case["quality"]["canonical_repeat_rate"] for case in cases]), 4) if cases else 0.0
    aggregate["mean_low_signal_rate"] = round(mean([case["quality"]["low_signal_rate"] for case in cases]), 4) if cases else 0.0
    return aggregate


def threshold_results(aggregate: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, bool]:
    results = {}
    for metric, threshold in thresholds.items():
        results[metric] = float(aggregate.get(metric, 0.0)) >= float(threshold)
    return results


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


def load_evaluation_set(path: Any) -> dict[str, Any]:
    return read_json(path)
