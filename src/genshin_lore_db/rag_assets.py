from __future__ import annotations

import argparse
import json
import os
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

from .io import ensure_dir, iter_jsonl, pretty_json_dumps, read_json, sha256_text, stable_json_dumps, write_json, write_jsonl
from .normalize import clean_text


LANGUAGE_LABELS = {
    "ko": "한국어",
    "zh-Hans": "중국어_간체",
    "ja": "일본어",
    "en": "영어",
    "und": "공통",
}

SOURCE_LABELS = {
    "project_amber": "엠버 프로젝트",
    "genshin_data_readable": "GenshinData readable",
    "dimbreath_textmap": "Dimbreath TextMap",
}

SOURCE_PRIORITY = {
    "project_amber": 10,
    "genshin_data_readable": 20,
    "dimbreath_textmap": 30,
}

KIND_PRIORITY = {
    "detail": 10,
    "deep": 20,
    "readable": 25,
    "list": 30,
}

QUEST_TYPE_LABELS = {
    "aq": "마신 임무",
    "lq": "전설 임무",
    "eq": "이벤트 임무",
    "wq": "월드 임무",
    "iq": "일일 의뢰",
}

CONTENT_CATEGORY = {
    "avatar": ("캐릭터", None),
    "weapon": ("무기", None),
    "reliquary": ("성유물", None),
    "gcg": ("일곱 성인의 소환", None),
    "quest": ("여행 기록", None),
    "achievement": ("업적", None),
    "food": ("아카이브", "음식"),
    "material": ("아카이브", "재료"),
    "furniture": ("아카이브", "가구"),
    "furnitureSuite": ("아카이브", "가구 세트"),
    "namecard": ("아카이브", "명함"),
    "monster": ("아카이브", "생물지"),
    "book": ("아카이브", "서적"),
    "elements": ("가이드북", "원소"),
    "advanced_avatar_guide": ("보조 데이터", "고급 가이드/캐릭터"),
    "advanced_weapon_guide": ("보조 데이터", "고급 가이드/무기"),
    "advanced_reliquary_guide": ("보조 데이터", "고급 가이드/성유물"),
    "avatarCurve": ("보조 데이터", "캐릭터 성장 곡선"),
    "weaponCurve": ("보조 데이터", "무기 성장 곡선"),
    "reliquaryCurve": ("보조 데이터", "성유물 성장 곡선"),
    "monsterCurve": ("보조 데이터", "몬스터 성장 곡선"),
    "event": ("보조 데이터", "이벤트"),
    "pronoun": ("보조 데이터", "대명사"),
    "everything": ("보조 데이터", "전체 목록"),
    "manualWeapon": ("보조 데이터", "수동 무기"),
    "combine": ("보조 데이터", "합성"),
    "dailyDungeon": ("보조 데이터", "요일 던전"),
    "upgrade": ("보조 데이터", "강화 비용"),
    "tower": ("보조 데이터", "나선 비경"),
    "static_changelog": ("보조 데이터", "변경 이력"),
    "readable": ("보조 데이터", "읽을거리"),
}

TEXT_SKIP_KEYS = {
    "icon",
    "route",
    "source_url",
    "content_hash",
    "raw_id",
    "fetched_at",
    "crawler_version",
    "raw_format",
    "metadata",
    "params",
}


def build_rag_assets(root: Path, *, include_textmap_index: bool = True) -> dict[str, Any]:
    root = root.resolve()
    raw_root = root / "data" / "raw"
    project_amber_raw_root = raw_root / "project_amber"
    processed_project_amber_root = root / "data" / "processed" / "project_amber"
    canonical_root = root / "data" / "canonical"

    raw_before = raw_fingerprint(project_amber_raw_root)
    quality_report = analyze_project_amber_processed(processed_project_amber_root, project_amber_raw_root)
    schema_report = write_unified_schemas(root)
    rag_report = build_unified_rag_files(canonical_root, root / "data" / "processed" / "rag")
    search_report = build_search_index(
        root / "data" / "processed" / "rag",
        canonical_root,
        root / "data" / "processed" / "search" / "lore_search.sqlite3",
        include_textmap_index=include_textmap_index,
    )
    raw_after = raw_fingerprint(project_amber_raw_root)

    quality_report["raw_integrity"] = {
        "before": raw_before,
        "after": raw_after,
        "unchanged_during_build": raw_before == raw_after,
    }
    write_quality_report(root / "data" / "processed" / "quality", quality_report)

    report = {
        "built_at": utc_now(),
        "raw_project_amber_unchanged": raw_before == raw_after,
        "quality": {
            "json_files": quality_report["processed"]["json_files"],
            "data_files": quality_report["processed"]["data_files"],
            "parse_errors": quality_report["processed"]["parse_errors"],
            "raw_ref_missing": quality_report["coverage"]["missing_raw_refs"],
            "raw_ref_extra": quality_report["coverage"]["extra_raw_refs"],
        },
        "schema": schema_report,
        "rag": rag_report,
        "search": search_report,
        "outputs": {
            "quality_report_json": str(root / "data" / "processed" / "quality" / "project_amber_quality_report.json"),
            "quality_report_md": str(root / "data" / "processed" / "quality" / "project_amber_quality_report.md"),
            "schema_dir": str(root / "data" / "processed" / "schema"),
            "rag_dir": str(root / "data" / "processed" / "rag"),
            "search_db": str(root / "data" / "processed" / "search" / "lore_search.sqlite3"),
        },
    }
    write_json(root / "data" / "processed" / "rag_assets_report.json", report)
    return report


def analyze_project_amber_processed(processed_root: Path, raw_root: Path) -> dict[str, Any]:
    processed_root = processed_root.resolve()
    raw_root = raw_root.resolve()
    report: dict[str, Any] = {
        "built_at": utc_now(),
        "processed_root": str(processed_root),
        "raw_root": str(raw_root),
        "processed": {
            "json_files": 0,
            "data_files": 0,
            "report_files": 0,
            "parse_errors": 0,
            "missing_title": 0,
            "null_payload": 0,
            "empty_payload": 0,
            "short_text_under_20": 0,
            "long_path_over_240": 0,
            "max_path_length": 0,
            "max_path": None,
        },
        "coverage": {
            "raw_json_files": 0,
            "processed_raw_refs": 0,
            "missing_raw_refs": 0,
            "extra_raw_refs": 0,
        },
        "by_language": {},
        "by_content_type": {},
        "duplicate_titles": {
            "groups": 0,
            "files_in_groups": 0,
            "samples": [],
        },
        "issue_samples": {
            "parse_errors": [],
            "missing_title": [],
            "null_payload": [],
            "empty_payload": [],
            "short_text_under_20": [],
            "long_path_over_240": [],
        },
    }
    language_counts: Counter[str] = Counter()
    content_type_counts: Counter[str] = Counter()
    title_groups: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    raw_files = {path.resolve().as_posix() for path in raw_root.rglob("*.json")}
    raw_refs: set[str] = set()

    for path in sorted(processed_root.rglob("*.json")):
        report["processed"]["json_files"] += 1
        resolved = str(path.resolve())
        path_length = len(resolved)
        if path_length > report["processed"]["max_path_length"]:
            report["processed"]["max_path_length"] = path_length
            report["processed"]["max_path"] = resolved
        if path_length > 240:
            report["processed"]["long_path_over_240"] += 1
            _sample(report["issue_samples"]["long_path_over_240"], str(path))

        try:
            data = read_json(path)
        except Exception as exc:  # noqa: BLE001
            report["processed"]["parse_errors"] += 1
            _sample(report["issue_samples"]["parse_errors"], {"path": str(path), "error": repr(exc)})
            continue

        if not isinstance(data, dict) or "payload" not in data:
            report["processed"]["report_files"] += 1
            continue

        report["processed"]["data_files"] += 1
        title = data.get("title")
        language = str(data.get("language") or "unknown")
        content_type = str(data.get("content_type") or "unknown")
        language_counts[LANGUAGE_LABELS.get(language, language)] += 1
        content_type_counts[content_type] += 1

        if not isinstance(title, str) or not title.strip():
            report["processed"]["missing_title"] += 1
            _sample(report["issue_samples"]["missing_title"], str(path))
            title = "<missing>"

        category_path = str(path.parent.relative_to(processed_root)) if processed_root in path.parents else str(path.parent)
        title_groups[(language, category_path, title.strip())].append(str(path))

        ref = data.get("raw_ref")
        if isinstance(ref, str) and ref.strip():
            raw_refs.add(Path(ref).resolve().as_posix())

        payload = data.get("payload")
        if payload is None:
            report["processed"]["null_payload"] += 1
            _sample(report["issue_samples"]["null_payload"], str(path))
            continue
        if payload in ({}, [], ""):
            report["processed"]["empty_payload"] += 1
            _sample(report["issue_samples"]["empty_payload"], str(path))

        text_chars = len("\n".join(iter_payload_strings(payload)))
        if text_chars < 20:
            report["processed"]["short_text_under_20"] += 1
            _sample(report["issue_samples"]["short_text_under_20"], {"path": str(path), "text_chars": text_chars})

    duplicate_samples: list[dict[str, Any]] = []
    duplicate_files = 0
    duplicate_groups = 0
    for (language, category_path, title), files in sorted(title_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        if len(files) <= 1:
            continue
        duplicate_groups += 1
        duplicate_files += len(files)
        if len(duplicate_samples) < 50:
            duplicate_samples.append(
                {
                    "language": LANGUAGE_LABELS.get(language, language),
                    "category_path": category_path,
                    "title": title,
                    "count": len(files),
                    "sample_paths": files[:10],
                }
            )

    missing_raw_refs = sorted(raw_files - raw_refs)
    extra_raw_refs = sorted(raw_refs - raw_files)
    report["coverage"] = {
        "raw_json_files": len(raw_files),
        "processed_raw_refs": len(raw_refs),
        "missing_raw_refs": len(missing_raw_refs),
        "extra_raw_refs": len(extra_raw_refs),
        "missing_raw_ref_samples": missing_raw_refs[:20],
        "extra_raw_ref_samples": extra_raw_refs[:20],
    }
    report["by_language"] = dict(sorted(language_counts.items()))
    report["by_content_type"] = dict(sorted(content_type_counts.items()))
    report["duplicate_titles"] = {
        "groups": duplicate_groups,
        "files_in_groups": duplicate_files,
        "samples": duplicate_samples,
    }
    return report


def write_quality_report(out_dir: Path, report: dict[str, Any]) -> None:
    ensure_dir(out_dir)
    write_json(out_dir / "project_amber_quality_report.json", report)
    lines = [
        "# 엠버 프로젝트 전처리 품질 검수 리포트",
        "",
        f"- 생성 시각: `{report['built_at']}`",
        f"- 전처리 루트: `{report['processed_root']}`",
        f"- RAW 루트: `{report['raw_root']}`",
        f"- JSON 파일: `{report['processed']['json_files']}`",
        f"- 데이터 파일: `{report['processed']['data_files']}`",
        f"- JSON 파싱 오류: `{report['processed']['parse_errors']}`",
        f"- RAW 참조 누락: `{report['coverage']['missing_raw_refs']}`",
        f"- RAW 참조 초과: `{report['coverage']['extra_raw_refs']}`",
        f"- 빌드 중 RAW 변경 없음: `{report.get('raw_integrity', {}).get('unchanged_during_build')}`",
        "",
        "## 주요 경고",
        "",
        f"- 제목 없음: `{report['processed']['missing_title']}`",
        f"- payload가 null: `{report['processed']['null_payload']}`",
        f"- payload가 빈 값: `{report['processed']['empty_payload']}`",
        f"- 추출 문자열 20자 미만: `{report['processed']['short_text_under_20']}`",
        f"- 경로 길이 240자 초과: `{report['processed']['long_path_over_240']}`",
        f"- 최대 경로 길이: `{report['processed']['max_path_length']}`",
        "",
        "## 언어별 파일 수",
        "",
    ]
    for language, count in report["by_language"].items():
        lines.append(f"- {language}: `{count}`")
    lines.extend(["", "## 콘텐츠 타입별 파일 수", ""])
    for content_type, count in report["by_content_type"].items():
        lines.append(f"- {content_type}: `{count}`")
    lines.extend(["", "## 중복 제목 그룹", ""])
    lines.append(f"- 그룹 수: `{report['duplicate_titles']['groups']}`")
    lines.append(f"- 해당 파일 수: `{report['duplicate_titles']['files_in_groups']}`")
    (out_dir / "project_amber_quality_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_unified_schemas(root: Path) -> dict[str, Any]:
    out_dir = root / "data" / "processed" / "schema"
    ensure_dir(out_dir)
    document_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "genshin-lore-unified-document.schema.json",
        "title": "원신 스토리 추측 프로젝트 통합 문서",
        "type": "object",
        "required": [
            "id",
            "original_id",
            "canonical_id",
            "source",
            "language",
            "language_label",
            "category",
            "content_type",
            "title",
            "text",
            "text_hash",
            "raw_refs",
            "metadata",
        ],
        "properties": {
            "id": {"type": "string", "description": "문서 단위 고유 ID"},
            "original_id": {"type": "string", "description": "정규화 단계에서 넘어온 원래 문서 ID"},
            "canonical_id": {"type": "string", "description": "언어/상세 수준이 달라도 같은 항목을 묶는 ID"},
            "parallel_group_id": {"type": "string", "description": "동일 항목 병렬 원문 그룹 ID"},
            "source": {"type": "string", "description": "수집 소스 코드"},
            "source_label": {"type": "string", "description": "사람이 읽는 소스명"},
            "source_priority": {"type": "integer", "description": "대표 문서 선택용 소스 우선순위. 낮을수록 우선"},
            "language": {"type": "string", "description": "언어 코드"},
            "language_label": {"type": "string", "description": "사람이 읽는 언어명"},
            "category": {"type": "string", "description": "최상위 분류"},
            "subcategory": {"type": ["string", "null"], "description": "하위 분류"},
            "content_type": {"type": "string", "description": "원천 콘텐츠 타입"},
            "officialness": {"type": "string", "description": "공식 텍스트/커뮤니티 해석 등 출처 성격"},
            "title": {"type": ["string", "null"], "description": "문서 제목"},
            "text": {"type": "string", "description": "검색/추론에 사용할 정규화 텍스트"},
            "text_hash": {"type": "string", "description": "정규화 텍스트 해시"},
            "duplicate_group_id": {"type": ["string", "null"], "description": "동일 텍스트 중복 그룹 ID"},
            "duplicate_status": {"type": "string", "enum": ["unique", "representative", "duplicate"]},
            "duplicate_of": {"type": ["string", "null"], "description": "중복 문서가 가리키는 대표 문서 ID"},
            "source_url": {"type": ["string", "null"], "description": "원천 URL"},
            "raw_refs": {"type": "array", "items": {"type": "string"}, "description": "원본 RAW 파일 참조"},
            "metadata": {"type": "object", "description": "원천별 부가 메타데이터"},
        },
        "additionalProperties": False,
    }
    chunk_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "genshin-lore-unified-chunk.schema.json",
        "title": "원신 스토리 추측 프로젝트 통합 검색 청크",
        "type": "object",
        "required": [
            "chunk_id",
            "document_id",
            "original_document_id",
            "canonical_id",
            "source",
            "language",
            "category",
            "content_type",
            "title",
            "ordinal",
            "text",
            "chunk_hash",
        ],
        "properties": {
            "chunk_id": {"type": "string"},
            "document_id": {"type": "string"},
            "original_document_id": {"type": "string"},
            "canonical_id": {"type": "string"},
            "parallel_group_id": {"type": "string"},
            "source": {"type": "string"},
            "source_label": {"type": "string"},
            "source_priority": {"type": "integer"},
            "language": {"type": "string"},
            "language_label": {"type": "string"},
            "category": {"type": "string"},
            "subcategory": {"type": ["string", "null"]},
            "content_type": {"type": "string"},
            "officialness": {"type": "string"},
            "title": {"type": ["string", "null"]},
            "ordinal": {"type": "integer"},
            "text": {"type": "string"},
            "chunk_hash": {"type": "string"},
            "duplicate_group_id": {"type": ["string", "null"]},
            "duplicate_status": {"type": "string", "enum": ["unique", "representative", "duplicate"]},
            "duplicate_of": {"type": ["string", "null"]},
            "source_url": {"type": ["string", "null"]},
            "raw_refs": {"type": "array", "items": {"type": "string"}},
            "metadata": {"type": "object"},
        },
        "additionalProperties": False,
    }
    write_json(out_dir / "unified_document.schema.json", document_schema)
    write_json(out_dir / "unified_chunk.schema.json", chunk_schema)
    (out_dir / "README.md").write_text(
        "\n".join(
            [
                "# 통합 스키마",
                "",
                "`unified_document.schema.json`은 문서 단위 RAG 원본의 공통 규격입니다.",
                "`unified_chunk.schema.json`은 검색 인덱스에 들어가는 청크 단위 규격입니다.",
                "",
                "핵심 원칙:",
                "",
                "- RAW 파일은 수정하지 않고 `raw_refs`로만 연결합니다.",
                "- 같은 항목의 언어별/출처별 문서는 `canonical_id`와 `parallel_group_id`로 묶습니다.",
                "- 완전히 같은 텍스트는 `duplicate_group_id`, `duplicate_status`, `duplicate_of`로 표시합니다.",
                "- `category`와 `subcategory`는 최종 한국어 보고서에서 바로 쓰기 쉬운 분류명입니다.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return {
        "schema_dir": str(out_dir),
        "files": ["unified_document.schema.json", "unified_chunk.schema.json", "README.md"],
    }


def build_unified_rag_files(canonical_root: Path, out_dir: Path) -> dict[str, Any]:
    ensure_dir(out_dir)
    documents_path = canonical_root / "documents.jsonl"
    chunks_path = canonical_root / "chunks.jsonl"
    duplicate_state = collect_duplicate_state(documents_path)
    doc_lookup: dict[str, dict[str, Any]] = {}
    doc_count = 0
    text_chars = 0
    by_language: Counter[str] = Counter()
    by_category: Counter[str] = Counter()
    by_source: Counter[str] = Counter()

    def unified_docs() -> Iterator[dict[str, Any]]:
        nonlocal doc_count, text_chars
        for doc in iter_jsonl(documents_path):
            unified = unify_document(doc, duplicate_state)
            doc_lookup[unified["id"]] = {
                key: unified[key]
                for key in [
                    "id",
                    "original_id",
                    "canonical_id",
                    "parallel_group_id",
                    "source",
                    "source_label",
                    "source_priority",
                    "language",
                    "language_label",
                    "category",
                    "subcategory",
                    "content_type",
                    "officialness",
                    "title",
                    "duplicate_group_id",
                    "duplicate_status",
                    "duplicate_of",
                    "source_url",
                    "raw_refs",
                    "metadata",
                ]
            }
            doc_count += 1
            text_chars += len(unified["text"])
            by_language[unified["language_label"]] += 1
            by_category[unified["category"]] += 1
            by_source[unified["source"]] += 1
            yield unified

    write_jsonl(out_dir / "documents.jsonl", unified_docs())

    chunk_count = 0
    chunk_chars = 0

    def unified_chunks() -> Iterator[dict[str, Any]]:
        nonlocal chunk_count, chunk_chars
        for chunk in iter_jsonl(chunks_path):
            doc_meta = doc_lookup.get(chunk["doc_id"])
            if doc_meta is None:
                doc_meta = doc_lookup.get(match_chunk_document_id(chunk, duplicate_state))
            if doc_meta is None:
                continue
            text = clean_text(chunk.get("text") or "")
            row = {
                "chunk_id": chunk["chunk_id"],
                "document_id": doc_meta["id"],
                "original_document_id": chunk["doc_id"],
                "canonical_id": doc_meta["canonical_id"],
                "parallel_group_id": doc_meta["parallel_group_id"],
                "source": doc_meta["source"],
                "source_label": doc_meta["source_label"],
                "source_priority": doc_meta["source_priority"],
                "language": doc_meta["language"],
                "language_label": doc_meta["language_label"],
                "category": doc_meta["category"],
                "subcategory": doc_meta["subcategory"],
                "content_type": doc_meta["content_type"],
                "officialness": doc_meta["officialness"],
                "title": doc_meta["title"],
                "ordinal": int(chunk.get("ordinal") or 0),
                "text": text,
                "chunk_hash": sha256_text(normalize_for_hash(text)),
                "duplicate_group_id": doc_meta["duplicate_group_id"],
                "duplicate_status": doc_meta["duplicate_status"],
                "duplicate_of": doc_meta["duplicate_of"],
                "source_url": doc_meta["source_url"],
                "raw_refs": doc_meta["raw_refs"],
                "metadata": {**doc_meta["metadata"], **(chunk.get("metadata") or {})},
            }
            chunk_count += 1
            chunk_chars += len(text)
            yield row

    write_jsonl(out_dir / "chunks.jsonl", unified_chunks())
    write_jsonl(out_dir / "document_duplicate_map.jsonl", duplicate_map_rows(duplicate_state))
    write_jsonl(out_dir / "duplicate_groups.jsonl", duplicate_group_rows(duplicate_state))
    write_jsonl(out_dir / "parallel_groups.jsonl", parallel_group_rows(duplicate_state))

    exact_groups = [group for group in duplicate_state["exact_groups"].values() if group["count"] > 1]
    parallel_groups = [group for group in duplicate_state["parallel_groups"].values() if group["count"] > 1]
    report = {
        "built_at": utc_now(),
        "documents": doc_count,
        "document_text_chars": text_chars,
        "chunks": chunk_count,
        "chunk_text_chars": chunk_chars,
        "by_language": dict(sorted(by_language.items())),
        "by_category": dict(sorted(by_category.items())),
        "by_source": dict(sorted(by_source.items())),
        "duplicates": {
            "exact_duplicate_groups": len(exact_groups),
            "documents_in_exact_duplicate_groups": sum(group["count"] for group in exact_groups),
            "parallel_groups": len(parallel_groups),
            "documents_in_parallel_groups": sum(group["count"] for group in parallel_groups),
        },
        "outputs": {
            "documents": str(out_dir / "documents.jsonl"),
            "chunks": str(out_dir / "chunks.jsonl"),
            "document_duplicate_map": str(out_dir / "document_duplicate_map.jsonl"),
            "duplicate_groups": str(out_dir / "duplicate_groups.jsonl"),
            "parallel_groups": str(out_dir / "parallel_groups.jsonl"),
        },
    }
    write_json(out_dir / "build_report.json", report)
    return report


def collect_duplicate_state(documents_path: Path) -> dict[str, Any]:
    original_counts: Counter[str] = Counter()
    for doc in iter_jsonl(documents_path):
        original_counts[str(doc["doc_id"])] += 1

    exact_groups: dict[str, dict[str, Any]] = {}
    parallel_groups: dict[str, dict[str, Any]] = {}
    doc_map: dict[str, dict[str, Any]] = {}
    occurrence_map: dict[str, str] = {}
    original_to_unique: dict[str, list[dict[str, str]]] = defaultdict(list)
    used_unique_ids: set[str] = set()

    for doc in iter_jsonl(documents_path):
        original_id = str(doc["doc_id"])
        language = str(doc.get("language") or "und")
        text = clean_text(doc.get("text") or "")
        normalized_text = normalize_for_hash(text)
        text_hash = sha256_text(normalized_text)
        occurrence_key = document_occurrence_key(doc, text_hash)
        doc_id = unique_document_id(original_id, doc, text_hash, original_counts[original_id], used_unique_ids)
        occurrence_map[occurrence_key] = doc_id
        original_to_unique[original_id].append(
            {
                "id": doc_id,
                "normalized_text": normalized_text,
                "text_hash": text_hash,
            }
        )
        duplicate_group_id = f"exact:{language}:{text_hash[:20]}"
        canonical_id = str(doc.get("canonical_group_id") or doc_id)
        title = doc.get("title")
        content_type = str(doc.get("content_type") or "unknown")
        source = str(doc.get("source") or "unknown")
        kind = str((doc.get("metadata") or {}).get("kind") or "unknown")
        rank = (SOURCE_PRIORITY.get(source, 100), KIND_PRIORITY.get(kind, 50), doc_id)

        group = exact_groups.setdefault(
            duplicate_group_id,
            {
                "duplicate_group_id": duplicate_group_id,
                "language": language,
                "text_hash": text_hash,
                "count": 0,
                "representative_doc_id": doc_id,
                "representative_rank": rank,
                "doc_ids": [],
                "titles": Counter(),
                "content_types": Counter(),
                "sources": Counter(),
            },
        )
        group["count"] += 1
        group["doc_ids"].append(doc_id)
        group["titles"][str(title or "<untitled>")] += 1
        group["content_types"][content_type] += 1
        group["sources"][source] += 1
        if rank < group["representative_rank"]:
            group["representative_rank"] = rank
            group["representative_doc_id"] = doc_id

        parallel = parallel_groups.setdefault(
            canonical_id,
            {
                "canonical_id": canonical_id,
                "count": 0,
                "doc_ids": [],
                "languages": Counter(),
                "titles": Counter(),
                "content_types": Counter(),
                "sources": Counter(),
            },
        )
        parallel["count"] += 1
        parallel["doc_ids"].append(doc_id)
        parallel["languages"][language] += 1
        parallel["titles"][str(title or "<untitled>")] += 1
        parallel["content_types"][content_type] += 1
        parallel["sources"][source] += 1

        doc_map[doc_id] = {
            "doc_id": doc_id,
            "original_id": original_id,
            "canonical_id": canonical_id,
            "duplicate_group_id": duplicate_group_id,
            "text_hash": text_hash,
        }

    for group in exact_groups.values():
        representative = group["representative_doc_id"]
        for doc_id in group["doc_ids"]:
            doc_map[doc_id]["duplicate_of"] = None if doc_id == representative else representative
            if group["count"] == 1:
                doc_map[doc_id]["duplicate_status"] = "unique"
                doc_map[doc_id]["duplicate_group_id"] = None
            elif doc_id == representative:
                doc_map[doc_id]["duplicate_status"] = "representative"
            else:
                doc_map[doc_id]["duplicate_status"] = "duplicate"

    return {
        "exact_groups": exact_groups,
        "parallel_groups": parallel_groups,
        "doc_map": doc_map,
        "occurrence_map": occurrence_map,
        "original_to_unique": original_to_unique,
    }


def document_occurrence_key(doc: dict[str, Any], text_hash: str) -> str:
    return stable_json_dumps(
        {
            "doc_id": doc.get("doc_id"),
            "canonical_group_id": doc.get("canonical_group_id"),
            "language": doc.get("language"),
            "source": doc.get("source"),
            "content_type": doc.get("content_type"),
            "raw_refs": doc.get("raw_refs") or [],
            "metadata": doc.get("metadata") or {},
            "text_hash": text_hash,
        }
    )


def unique_document_id(
    original_id: str,
    doc: dict[str, Any],
    text_hash: str,
    original_count: int,
    used_unique_ids: set[str],
) -> str:
    if original_count <= 1 and original_id not in used_unique_ids:
        used_unique_ids.add(original_id)
        return original_id
    suffix = sha256_text(
        stable_json_dumps(
            {
                "raw_refs": doc.get("raw_refs") or [],
                "metadata": doc.get("metadata") or {},
                "text_hash": text_hash,
            }
        )
    )[:12]
    candidate = f"{original_id}:occurrence:{suffix}"
    if candidate not in used_unique_ids:
        used_unique_ids.add(candidate)
        return candidate
    index = 2
    while True:
        indexed = f"{candidate}:{index}"
        if indexed not in used_unique_ids:
            used_unique_ids.add(indexed)
            return indexed
        index += 1


def match_chunk_document_id(chunk: dict[str, Any], duplicate_state: dict[str, Any]) -> str | None:
    original_id = str(chunk.get("doc_id") or "")
    candidates = duplicate_state["original_to_unique"].get(original_id) or []
    if not candidates:
        return None
    text = normalize_for_hash(chunk.get("text") or "")
    text_hash = sha256_text(text)
    for candidate in candidates:
        if candidate["text_hash"] == text_hash:
            return candidate["id"]
    for candidate in candidates:
        normalized = candidate["normalized_text"]
        if text and (text in normalized or normalized in text):
            return candidate["id"]
    return candidates[0]["id"]


def unify_document(doc: dict[str, Any], duplicate_state: dict[str, Any]) -> dict[str, Any]:
    metadata = dict(doc.get("metadata") or {})
    content_type = str(doc.get("content_type") or "unknown")
    category, subcategory = classify_document(content_type, metadata)
    language = str(doc.get("language") or "und")
    source = str(doc.get("source") or "unknown")
    text = clean_text(doc.get("text") or "")
    doc_id = str(doc["doc_id"])
    text_hash = sha256_text(normalize_for_hash(text))
    occurrence_key = document_occurrence_key(doc, text_hash)
    unique_id = duplicate_state["occurrence_map"][occurrence_key]
    duplicate = duplicate_state["doc_map"][unique_id]
    return {
        "id": unique_id,
        "original_id": doc_id,
        "canonical_id": str(doc.get("canonical_group_id") or doc_id),
        "parallel_group_id": str(doc.get("canonical_group_id") or doc_id),
        "source": source,
        "source_label": SOURCE_LABELS.get(source, source),
        "source_priority": SOURCE_PRIORITY.get(source, 100),
        "language": language,
        "language_label": LANGUAGE_LABELS.get(language, language),
        "category": category,
        "subcategory": subcategory,
        "content_type": content_type,
        "officialness": str(doc.get("officialness") or "unknown"),
        "title": doc.get("title"),
        "text": text,
        "text_hash": duplicate["text_hash"],
        "duplicate_group_id": duplicate.get("duplicate_group_id"),
        "duplicate_status": duplicate["duplicate_status"],
        "duplicate_of": duplicate.get("duplicate_of"),
        "source_url": doc.get("source_url"),
        "raw_refs": list(doc.get("raw_refs") or []),
        "metadata": metadata,
    }


def classify_document(content_type: str, metadata: dict[str, Any]) -> tuple[str, str | None]:
    category, subcategory = CONTENT_CATEGORY.get(content_type, ("보조 데이터", content_type))
    if content_type == "quest":
        quest_type = metadata.get("quest_type")
        subcategory = QUEST_TYPE_LABELS.get(str(quest_type), "기타")
    return category, subcategory


def duplicate_map_rows(duplicate_state: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for doc_id, row in sorted(duplicate_state["doc_map"].items()):
        yield {
            "doc_id": doc_id,
            "original_id": row["original_id"],
            "canonical_id": row["canonical_id"],
            "duplicate_group_id": row.get("duplicate_group_id"),
            "duplicate_status": row["duplicate_status"],
            "duplicate_of": row.get("duplicate_of"),
            "text_hash": row["text_hash"],
        }


def duplicate_group_rows(duplicate_state: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for group_id, group in sorted(duplicate_state["exact_groups"].items()):
        if group["count"] <= 1:
            continue
        yield {
            "duplicate_group_id": group_id,
            "language": group["language"],
            "text_hash": group["text_hash"],
            "count": group["count"],
            "representative_doc_id": group["representative_doc_id"],
            "sources": dict(group["sources"].most_common()),
            "content_types": dict(group["content_types"].most_common()),
            "sample_titles": [title for title, _ in group["titles"].most_common(20)],
            "sample_doc_ids": group["doc_ids"][:50],
        }


def parallel_group_rows(duplicate_state: dict[str, Any]) -> Iterator[dict[str, Any]]:
    for canonical_id, group in sorted(duplicate_state["parallel_groups"].items()):
        if group["count"] <= 1:
            continue
        yield {
            "canonical_id": canonical_id,
            "count": group["count"],
            "languages": dict(group["languages"].most_common()),
            "sources": dict(group["sources"].most_common()),
            "content_types": dict(group["content_types"].most_common()),
            "sample_titles": [title for title, _ in group["titles"].most_common(20)],
            "sample_doc_ids": group["doc_ids"][:50],
        }


def build_search_index(
    rag_dir: Path,
    canonical_root: Path,
    db_path: Path,
    *,
    include_textmap_index: bool,
) -> dict[str, Any]:
    ensure_dir(db_path.parent)
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")
    create_search_schema(conn, include_textmap_index=include_textmap_index)

    documents = insert_documents(conn, rag_dir / "documents.jsonl")
    chunks = insert_chunks(conn, rag_dir / "chunks.jsonl")
    textmap_entries = 0
    if include_textmap_index:
        textmap_entries = insert_textmap_entries(conn, canonical_root / "textmap_entries.jsonl")

    rebuild_fts(conn, include_textmap_index=include_textmap_index)
    conn.execute("PRAGMA optimize")
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    conn.close()

    report = {
        "built_at": utc_now(),
        "db_path": str(db_path),
        "db_size_bytes": db_path.stat().st_size,
        "documents": documents,
        "chunks": chunks,
        "textmap_entries": textmap_entries,
        "fts": {
            "chunks_unicode": True,
            "chunks_trigram": True,
            "textmap_unicode": include_textmap_index,
            "textmap_trigram": include_textmap_index,
        },
        "sqlite_integrity_check": integrity,
    }
    write_json(db_path.parent / "search_report.json", report)
    return report


def create_search_schema(conn: sqlite3.Connection, *, include_textmap_index: bool) -> None:
    conn.executescript(
        """
        CREATE TABLE documents (
            doc_id TEXT PRIMARY KEY,
            original_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            parallel_group_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_label TEXT NOT NULL,
            source_priority INTEGER NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            content_type TEXT NOT NULL,
            officialness TEXT NOT NULL,
            title TEXT,
            text TEXT NOT NULL,
            text_hash TEXT NOT NULL,
            duplicate_group_id TEXT,
            duplicate_status TEXT NOT NULL,
            duplicate_of TEXT,
            source_url TEXT,
            raw_refs_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE TABLE chunks (
            rowid INTEGER PRIMARY KEY,
            chunk_id TEXT UNIQUE NOT NULL,
            document_id TEXT NOT NULL,
            original_document_id TEXT NOT NULL,
            canonical_id TEXT NOT NULL,
            parallel_group_id TEXT NOT NULL,
            source TEXT NOT NULL,
            source_label TEXT NOT NULL,
            source_priority INTEGER NOT NULL,
            language TEXT NOT NULL,
            language_label TEXT NOT NULL,
            category TEXT NOT NULL,
            subcategory TEXT,
            content_type TEXT NOT NULL,
            officialness TEXT NOT NULL,
            title TEXT,
            ordinal INTEGER NOT NULL,
            text TEXT NOT NULL,
            chunk_hash TEXT NOT NULL,
            duplicate_group_id TEXT,
            duplicate_status TEXT NOT NULL,
            duplicate_of TEXT,
            source_url TEXT,
            raw_refs_json TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        );

        CREATE INDEX idx_chunks_document_id ON chunks(document_id);
        CREATE INDEX idx_chunks_language ON chunks(language);
        CREATE INDEX idx_chunks_category ON chunks(category);
        CREATE INDEX idx_chunks_content_type ON chunks(content_type);
        CREATE INDEX idx_chunks_canonical_id ON chunks(canonical_id);
        CREATE INDEX idx_chunks_duplicate_status ON chunks(duplicate_status);

        CREATE VIRTUAL TABLE chunks_fts_unicode USING fts5(
            title,
            text,
            content='chunks',
            content_rowid='rowid',
            tokenize='unicode61 remove_diacritics 2'
        );

        CREATE VIRTUAL TABLE chunks_fts_trigram USING fts5(
            title,
            text,
            content='chunks',
            content_rowid='rowid',
            tokenize='trigram'
        );
        """
    )
    if include_textmap_index:
        conn.executescript(
            """
            CREATE TABLE textmap_entries (
                rowid INTEGER PRIMARY KEY,
                textmap_id TEXT NOT NULL,
                language TEXT NOT NULL,
                language_label TEXT NOT NULL,
                text TEXT NOT NULL,
                source TEXT NOT NULL,
                source_label TEXT NOT NULL,
                source_url TEXT,
                raw_ref TEXT,
                content_hash TEXT
            );

            CREATE INDEX idx_textmap_language ON textmap_entries(language);
            CREATE INDEX idx_textmap_textmap_id ON textmap_entries(textmap_id);

            CREATE VIRTUAL TABLE textmap_fts_unicode USING fts5(
                text,
                content='textmap_entries',
                content_rowid='rowid',
                tokenize='unicode61 remove_diacritics 2'
            );

            CREATE VIRTUAL TABLE textmap_fts_trigram USING fts5(
                text,
                content='textmap_entries',
                content_rowid='rowid',
                tokenize='trigram'
            );
            """
        )


def insert_documents(conn: sqlite3.Connection, path: Path) -> int:
    sql = """
        INSERT INTO documents (
            doc_id, original_id, canonical_id, parallel_group_id, source, source_label, source_priority,
            language, language_label, category, subcategory, content_type, officialness,
            title, text, text_hash, duplicate_group_id, duplicate_status, duplicate_of,
            source_url, raw_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = []
    count = 0
    for doc in iter_jsonl(path):
        rows.append(
            (
                doc["id"],
                doc["original_id"],
                doc["canonical_id"],
                doc["parallel_group_id"],
                doc["source"],
                doc["source_label"],
                doc["source_priority"],
                doc["language"],
                doc["language_label"],
                doc["category"],
                doc["subcategory"],
                doc["content_type"],
                doc["officialness"],
                doc["title"],
                doc["text"],
                doc["text_hash"],
                doc["duplicate_group_id"],
                doc["duplicate_status"],
                doc["duplicate_of"],
                doc["source_url"],
                stable_json_dumps(doc["raw_refs"]),
                stable_json_dumps(doc["metadata"]),
            )
        )
        if len(rows) >= 1000:
            conn.executemany(sql, rows)
            count += len(rows)
            rows.clear()
    if rows:
        conn.executemany(sql, rows)
        count += len(rows)
    conn.commit()
    return count


def insert_chunks(conn: sqlite3.Connection, path: Path) -> int:
    sql = """
        INSERT INTO chunks (
            chunk_id, document_id, original_document_id, canonical_id, parallel_group_id, source, source_label,
            source_priority, language, language_label, category, subcategory, content_type,
            officialness, title, ordinal, text, chunk_hash, duplicate_group_id,
            duplicate_status, duplicate_of, source_url, raw_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = []
    count = 0
    for chunk in iter_jsonl(path):
        rows.append(
            (
                chunk["chunk_id"],
                chunk["document_id"],
                chunk["original_document_id"],
                chunk["canonical_id"],
                chunk["parallel_group_id"],
                chunk["source"],
                chunk["source_label"],
                chunk["source_priority"],
                chunk["language"],
                chunk["language_label"],
                chunk["category"],
                chunk["subcategory"],
                chunk["content_type"],
                chunk["officialness"],
                chunk["title"],
                chunk["ordinal"],
                chunk["text"],
                chunk["chunk_hash"],
                chunk["duplicate_group_id"],
                chunk["duplicate_status"],
                chunk["duplicate_of"],
                chunk["source_url"],
                stable_json_dumps(chunk["raw_refs"]),
                stable_json_dumps(chunk["metadata"]),
            )
        )
        if len(rows) >= 2000:
            conn.executemany(sql, rows)
            count += len(rows)
            rows.clear()
    if rows:
        conn.executemany(sql, rows)
        count += len(rows)
    conn.commit()
    return count


def insert_textmap_entries(conn: sqlite3.Connection, path: Path) -> int:
    if not path.exists():
        return 0
    sql = """
        INSERT INTO textmap_entries (
            textmap_id, language, language_label, text, source, source_label,
            source_url, raw_ref, content_hash
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    rows = []
    count = 0
    for row in iter_jsonl(path):
        language = str(row.get("language") or "und")
        source = str(row.get("source") or "dimbreath_textmap")
        rows.append(
            (
                str(row.get("textmap_id") or ""),
                language,
                LANGUAGE_LABELS.get(language, language),
                clean_text(row.get("text") or ""),
                source,
                SOURCE_LABELS.get(source, source),
                row.get("source_url"),
                row.get("raw_ref"),
                row.get("content_hash"),
            )
        )
        if len(rows) >= 5000:
            conn.executemany(sql, rows)
            count += len(rows)
            rows.clear()
    if rows:
        conn.executemany(sql, rows)
        count += len(rows)
    conn.commit()
    return count


def rebuild_fts(conn: sqlite3.Connection, *, include_textmap_index: bool) -> None:
    conn.execute("INSERT INTO chunks_fts_unicode(chunks_fts_unicode) VALUES('rebuild')")
    conn.execute("INSERT INTO chunks_fts_trigram(chunks_fts_trigram) VALUES('rebuild')")
    if include_textmap_index:
        conn.execute("INSERT INTO textmap_fts_unicode(textmap_fts_unicode) VALUES('rebuild')")
        conn.execute("INSERT INTO textmap_fts_trigram(textmap_fts_trigram) VALUES('rebuild')")
    conn.commit()


def search_lore(
    db_path: Path,
    query: str,
    *,
    language: str | None = None,
    category: str | None = None,
    content_type: str | None = None,
    limit: int = 10,
    mode: str = "unicode",
    include_textmap: bool = False,
) -> list[dict[str, Any]]:
    table = "chunks_fts_trigram" if mode == "trigram" else "chunks_fts_unicode"
    match = fts_query(query)
    filters = []
    params: list[Any] = [match]
    if language:
        filters.append("c.language = ?")
        params.append(language)
    if category:
        filters.append("c.category = ?")
        params.append(category)
    if content_type:
        filters.append("c.content_type = ?")
        params.append(content_type)
    where = f"{table} MATCH ?"
    if filters:
        where += " AND " + " AND ".join(filters)
    sql = f"""
        SELECT
            'chunk' AS result_type,
            c.chunk_id AS id,
            c.document_id,
            c.language,
            c.language_label,
            c.category,
            c.subcategory,
            c.content_type,
            c.title,
            c.text,
            c.source,
            c.source_url,
            bm25({table}) AS rank
        FROM {table}
        JOIN chunks c ON c.rowid = {table}.rowid
        WHERE {where}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    rows = [dict(row) for row in conn.execute(sql, params).fetchall()]
    if include_textmap:
        textmap_table = "textmap_fts_trigram" if mode == "trigram" else "textmap_fts_unicode"
        textmap_params: list[Any] = [match]
        textmap_filters = []
        if language:
            textmap_filters.append("t.language = ?")
            textmap_params.append(language)
        textmap_where = f"{textmap_table} MATCH ?"
        if textmap_filters:
            textmap_where += " AND " + " AND ".join(textmap_filters)
        textmap_sql = f"""
            SELECT
                'textmap' AS result_type,
                t.textmap_id AS id,
                NULL AS document_id,
                t.language,
                t.language_label,
                'TextMap' AS category,
                NULL AS subcategory,
                'textmap' AS content_type,
                t.textmap_id AS title,
                t.text,
                t.source,
                t.source_url,
                bm25({textmap_table}) AS rank
            FROM {textmap_table}
            JOIN textmap_entries t ON t.rowid = {textmap_table}.rowid
            WHERE {textmap_where}
            ORDER BY rank
            LIMIT ?
        """
        textmap_params.append(limit)
        rows.extend(dict(row) for row in conn.execute(textmap_sql, textmap_params).fetchall())
        rows.sort(key=lambda row: row["rank"])
        rows = rows[:limit]
    conn.close()
    return rows


def raw_fingerprint(raw_root: Path) -> dict[str, Any]:
    files = sorted(path for path in raw_root.rglob("*") if path.is_file())
    digest_parts = []
    total_bytes = 0
    for path in files:
        file_hash = sha256_file(path)
        stat = path.stat()
        total_bytes += stat.st_size
        digest_parts.append(f"{path.relative_to(raw_root).as_posix()}\0{stat.st_size}\0{file_hash}")
    return {
        "root": str(raw_root.resolve()),
        "files": len(files),
        "bytes": total_bytes,
        "fingerprint_sha256": sha256_text("\n".join(digest_parts)),
    }


def sha256_file(path: Path, *, block_size: int = 1024 * 1024) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def iter_payload_strings(payload: Any, *, parent_key: str | None = None) -> Iterator[str]:
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in TEXT_SKIP_KEYS:
                continue
            yield from iter_payload_strings(value, parent_key=str(key))
        return
    if isinstance(payload, list):
        for value in payload:
            yield from iter_payload_strings(value, parent_key=parent_key)
        return
    if isinstance(payload, str):
        text = clean_text(payload)
        if text:
            yield text


def normalize_for_hash(text: str) -> str:
    return " ".join(clean_text(text).split()).casefold()


def fts_query(query: str) -> str:
    tokens = [token.strip() for token in query.split() if token.strip()]
    if not tokens:
        return '""'
    return " AND ".join(f'"{token.replace(chr(34), chr(34) + chr(34))}"' for token in tokens)


def _sample(samples: list[Any], value: Any, *, limit: int = 50) -> None:
    if len(samples) < limit:
        samples.append(value)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[2]))
    parser.add_argument("--skip-textmap-index", action="store_true")
    args = parser.parse_args(argv)
    report = build_rag_assets(Path(args.root), include_textmap_index=not args.skip_textmap_index)
    print(pretty_json_dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
