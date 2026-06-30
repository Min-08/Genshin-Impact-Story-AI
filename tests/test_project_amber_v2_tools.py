from __future__ import annotations

import json
import importlib.util
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from genshin_lore_db.io import stable_json_dumps
from genshin_lore_db.pipeline.project_amber_v2 import create_v2_schema, populate_v2_fts
from genshin_lore_db.pipeline.project_amber_v2_audit import audit_project_amber_v2
from genshin_lore_db.pipeline.project_amber_v2_evaluation import evaluate_project_amber_v2_search
from genshin_lore_db.search_engine.evidence_store import EvidenceStore
from genshin_lore_db.search_engine.source_reader import ProjectAmberV2SourceReader
from genshin_lore_db.search_engine.v2_engine import ProjectAmberV2SearchEngine, matched_v2_terms


def test_project_amber_v2_audit_passes_on_consistent_fixture(tmp_path: Path) -> None:
    canonical_root, db_path = build_tiny_v2_fixture(tmp_path)

    report = audit_project_amber_v2(tmp_path, canonical_root=canonical_root, search_db=db_path)

    assert report["ok"] is True
    assert report["jsonl"]["counts"]["text_units"] == 8
    assert report["sqlite"]["table_counts"]["text_units"] == 8
    assert report["sqlite"]["integrity_check"] == "ok"


def test_project_amber_v2_audit_catches_count_mismatch(tmp_path: Path) -> None:
    canonical_root, db_path = build_tiny_v2_fixture(tmp_path)
    build_report = json.loads((canonical_root / "build_report.json").read_text(encoding="utf-8"))
    build_report["counts"]["text_units"] = 999
    write_json(canonical_root / "build_report.json", build_report)

    report = audit_project_amber_v2(tmp_path, canonical_root=canonical_root, search_db=db_path)

    assert report["ok"] is False
    assert any(issue["code"] == "jsonl_count_mismatch" for issue in report["issues"])
    assert not any(issue["code"] == "sqlite_count_mismatch" for issue in report["issues"])


def test_source_reader_reads_unit_window_document_and_parallel(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    unit = reader.read_unit("project_amber:quest:1:ko:detail:unit:1")
    window = reader.read_window("project_amber:quest:1:ko:detail:unit:1", before=1, after=1)
    document = reader.read_document("project_amber:quest:1:ko:detail")
    parallel = reader.read_parallel("project_amber:quest:1:ko:detail:unit:0")

    assert unit is not None
    assert unit["text"] == "세계수는 기억을 기록한다."
    assert window is not None
    assert [row["unit_id"] for row in window["units"]] == [
        "project_amber:quest:1:ko:detail:unit:0",
        "project_amber:quest:1:ko:detail:unit:1",
        "project_amber:quest:1:ko:detail:unit:2",
    ]
    assert window["document_title"] == "세계수 테스트"
    assert window["section_id"] == "project_amber:quest:1:ko:detail:section:0"
    assert window["source_level"] == "L0"
    assert "expand_before" in window["next_actions"]
    assert "pin_evidence" in window["next_actions"]
    assert document is not None
    assert len(document["units"]) == 4
    assert parallel is not None
    assert {row["language"] for row in parallel["units"]} == {"en", "ko"}


def test_source_reader_limits_sections_and_reports_parallel_missing_languages(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    section = reader.read_section("project_amber:quest:1:ko:detail:section:0", max_units=2)
    parallel = reader.read_parallel("project_amber:quest:1:ko:detail:unit:0", languages=["ko", "en", "ja"])

    assert section is not None
    assert section["unit_count"] == 4
    assert section["included_unit_count"] == 2
    assert [row["unit_id"] for row in section["units"]] == [
        "project_amber:quest:1:ko:detail:unit:0",
        "project_amber:quest:1:ko:detail:unit:1",
    ]
    assert parallel is not None
    assert [block["language"] for block in parallel["blocks"]] == ["ko", "en", "ja"]
    assert [block["found"] for block in parallel["blocks"]] == [True, True, False]
    assert parallel["missing_languages"] == ["ja"]
    assert [row["language"] for row in parallel["units"]] == ["ko", "en"]


def test_source_reader_expands_window_without_crossing_document_boundary(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    base = reader.read_window("project_amber:quest:1:ko:detail:unit:1", before=0, after=1)
    expanded_before = reader.expand_window(base["window_id"], direction="before", amount=2)
    expanded_after = reader.expand_window(base["window_id"], direction="after", amount=5)

    assert [row["unit_id"] for row in base["units"]] == [
        "project_amber:quest:1:ko:detail:unit:1",
        "project_amber:quest:1:ko:detail:unit:2",
    ]
    assert expanded_before is not None
    assert [row["unit_id"] for row in expanded_before["units"]] == [
        "project_amber:quest:1:ko:detail:unit:0",
        "project_amber:quest:1:ko:detail:unit:1",
        "project_amber:quest:1:ko:detail:unit:2",
    ]
    assert expanded_after is not None
    assert [row["unit_id"] for row in expanded_after["units"]] == [
        "project_amber:quest:1:ko:detail:unit:1",
        "project_amber:quest:1:ko:detail:unit:2",
        "project_amber:quest:1:ko:detail:unit:3",
    ]


def test_source_reader_rejects_invalid_window_expansion(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    with pytest.raises(ValueError, match="window_id"):
        reader.expand_window("bad-window-id", direction="before", amount=1)
    with pytest.raises(ValueError, match="direction"):
        reader.expand_window("project_amber:quest:1:ko:detail:unit:1:window:0:1", direction="sideways", amount=1)
    with pytest.raises(ValueError, match="positive integer"):
        reader.expand_window("project_amber:quest:1:ko:detail:unit:1:window:0:1", direction="after", amount=0)


def test_source_reader_pins_document_and_unit_evidence(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    document_pin = reader.pin_evidence(
        "project_amber:quest:1:ko:detail",
        4,
        17,
        role="supports",
        source_level="L0",
        note="memory reference",
        hypothesis_ids=["H-001"],
    )
    repeated_document_pin = reader.pin_evidence(
        "project_amber:quest:1:ko:detail",
        4,
        17,
        role="supports",
        source_level="L0",
        note="memory reference",
        hypothesis_ids=["H-001"],
    )
    unit_pin = reader.pin_unit_evidence(
        "project_amber:quest:1:ko:detail:unit:1",
        0,
        3,
        role="context",
        source_level="L0",
    )

    assert document_pin is not None
    assert document_pin["schema_version"] == "evidence_pin.v0.1"
    assert document_pin["evidence_id"] == repeated_document_pin["evidence_id"]
    assert document_pin["excerpt"] == "세계수는 기억을 기록한다"
    assert document_pin["document_id"] == "project_amber:quest:1:ko:detail"
    assert document_pin["unit_id"] is None
    assert document_pin["role"] == "supports"
    assert document_pin["source_level"] == "L0"
    assert document_pin["hypothesis_ids"] == ["H-001"]
    assert unit_pin is not None
    assert unit_pin["excerpt"] == "세계수"
    assert unit_pin["unit_id"] == "project_amber:quest:1:ko:detail:unit:1"
    assert unit_pin["section_id"] == "project_amber:quest:1:ko:detail:section:0"
    assert unit_pin["role"] == "context"


def test_source_reader_rejects_invalid_evidence_pins(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)

    with pytest.raises(ValueError, match="end_char"):
        reader.pin_unit_evidence("project_amber:quest:1:ko:detail:unit:1", 2, 2, role="supports")
    with pytest.raises(ValueError, match="outside"):
        reader.pin_unit_evidence("project_amber:quest:1:ko:detail:unit:1", 0, 200, role="supports")
    with pytest.raises(ValueError, match="role"):
        reader.pin_unit_evidence("project_amber:quest:1:ko:detail:unit:1", 0, 2, role="unknown")
    with pytest.raises(ValueError, match="source_level"):
        reader.pin_unit_evidence("project_amber:quest:1:ko:detail:unit:1", 0, 2, role="supports", source_level="official")


def test_evidence_store_saves_lists_shows_and_dedupes(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)
    store = EvidenceStore.open(db_path, workspace_id="default")
    evidence = reader.pin_unit_evidence(
        "project_amber:quest:1:ko:detail:unit:1",
        0,
        3,
        role="supports",
        note="Irminsul source",
    )

    assert evidence is not None
    saved = store.append(evidence, created_at="2026-06-30T00:00:00+00:00")
    duplicate = store.append(evidence, created_at="2026-07-01T00:00:00+00:00")
    rows = store.list()

    assert saved["created"] is True
    assert duplicate["created"] is False
    assert store.path == tmp_path / "data" / "workspaces" / "default" / "evidence_pins.jsonl"
    assert len(rows) == 1
    assert rows[0]["workspace_id"] == "default"
    assert rows[0]["created_at"] == "2026-06-30T00:00:00+00:00"
    assert rows[0]["source_url"] is None
    assert store.get(rows[0]["evidence_id"]) == rows[0]
    assert store.list(role="supports") == rows
    assert store.list(query="Irminsul") == rows
    assert EvidenceStore.open(db_path, workspace_id="lab").list() == []


def test_read_source_cli_expands_pins_and_preserves_missing_exit_code(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "read_source.py"

    expand = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db",
            str(db_path),
            "expand-window",
            "project_amber:quest:1:ko:detail:unit:1:window:0:1",
            "--direction",
            "after",
            "--amount",
            "2",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert expand.returncode == 0
    expand_output = json.loads(expand.stdout)
    assert [row["unit_id"] for row in expand_output["units"]] == [
        "project_amber:quest:1:ko:detail:unit:1",
        "project_amber:quest:1:ko:detail:unit:2",
        "project_amber:quest:1:ko:detail:unit:3",
    ]

    pin = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db",
            str(db_path),
            "pin-unit",
            "project_amber:quest:1:ko:detail:unit:1",
            "--start-char",
            "0",
            "--end-char",
            "3",
            "--role",
            "supports",
            "--source-level",
            "L0",
            "--note",
            "cli pin",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert pin.returncode == 0
    pin_output = json.loads(pin.stdout)
    assert pin_output["excerpt"] == "세계수"
    assert pin_output["note"] == "cli pin"

    missing = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db",
            str(db_path),
            "unit",
            "missing-unit",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    assert missing.returncode == 2


def test_project_amber_v2_evaluator_scores_required_fragments(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    evaluation_set = {
        "version": "test",
        "default_limit": 5,
        "cases": [
            {
                "id": "irminsul_fixture",
                "query": "세계수",
                "language": "ko",
                "content_type": "quest",
                "expected_canonical_ids": ["project_amber:quest:1"],
                "expected_content_types": ["quest"],
                "expected_languages": ["ko"],
                "required_fragments": ["세계수"],
            }
        ],
        "thresholds": {"required_fragment_recall": 1.0},
    }

    report = evaluate_project_amber_v2_search(db_path, evaluation_set)

    assert report["aggregate"]["canonical_recall_at_k"] == 1.0
    assert report["aggregate"]["required_fragment_recall"] == 1.0
    assert report["passed_thresholds"]["required_fragment_recall"] is True


def test_project_amber_v2_search_engine_returns_v2_shape(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.search("Irminsul", language="en", content_type="quest", limit=1)

    assert result["engine"]["db_version"] == "v2"
    assert result["mode"] == "search"
    assert result["retrieval"]["fallback_used"] is False
    assert result["results"][0]["result_type"] == "text_unit"
    assert result["results"][0]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"
    assert result["results"][0]["score"] > 0


def test_project_amber_v2_search_falls_back_to_component_terms_when_strict_query_is_empty(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.search("memories Travelers", language="en", content_type="quest", limit=4)
    unit_ids = {hit["unit_id"] for hit in result["results"] if hit.get("unit_id")}

    assert result["retrieval"]["fallback_used"] is True
    assert result["retrieval"]["fallback_type"] == "component_terms"
    assert result["retrieval"]["fallback_terms"] == ["memories", "Travelers"]
    assert "project_amber:quest:1:en:detail:unit:1" in unit_ids
    assert "project_amber:quest:1:en:detail:unit:3" in unit_ids
    assert all(hit["result_type"] == "text_unit" for hit in result["results"])
    assert all(hit["retrieval_fallback"]["type"] == "component_terms" for hit in result["results"])


def test_project_amber_v2_matched_terms_ignore_one_character_overlaps() -> None:
    expansion = {
        "terms": [
            {"term": "I", "normalized": "i", "source": "query", "concept_id": None, "level": 0},
            {"term": "Irminsul", "normalized": "irminsul", "source": "query", "concept_id": None, "level": 0},
        ]
    }

    matched = matched_v2_terms({"title": "", "speaker": "", "text": "Irminsul records memories."}, expansion)

    assert [item["term"] for item in matched] == ["Irminsul"]


def test_project_amber_v2_search_results_are_source_readable(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)
    reader = ProjectAmberV2SourceReader(db_path)

    result = engine.search("Irminsul", language="en", content_type="quest", limit=1)
    hit = result["results"][0]
    window_result = reader.read_result_window(hit, before=0, after=0)
    missing_result = reader.read_result_window({"result_type": "textmap", "textmap_id": "1", "text": "Irminsul"})

    assert {
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
    }.issubset(hit)
    assert hit["chunk_id"] == hit["unit_id"]
    assert hit["section_id"] == "project_amber:quest:1:en:detail:section:0"
    assert window_result["ok"] is True
    assert window_result["window"]["center_unit_id"] == hit["unit_id"]
    assert missing_result["ok"] is False
    assert missing_result["error"]["code"] == "source_reader_mapping_missing"


def test_project_amber_v2_search_with_window_attaches_source_context(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.search("Irminsul", language="en", content_type="quest", limit=1, with_window=True)

    hit = result["results"][0]
    assert hit["source_reader"]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"
    assert hit["source_window"]["center"]["text"] == "Irminsul"
    assert hit["source_window"]["window_id"] == "project_amber:quest:1:en:detail:unit:0:window:3:3"


def test_project_amber_v2_investigate_preserves_unit_id_in_evidence_pack(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.investigate("Irminsul", language="en", content_type="quest", limit=1)

    assert result["engine"]["db_version"] == "v2"
    assert result["evidence_pack"]["sources"][0]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"
    assert result["evidence_pack"]["groups"][0]["support_type"] == "direct"


def test_project_amber_v2_investigate_uses_component_fallback_for_candidate_evidence(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.investigate("memories Travelers", language="en", content_type="quest", limit=4)
    candidate_unit_ids = {item["unit_id"] for item in result["candidate_evidence"]}

    assert result["retrieval"]["fallback_used"] is True
    assert "project_amber:quest:1:en:detail:unit:1" in candidate_unit_ids
    assert "project_amber:quest:1:en:detail:unit:3" in candidate_unit_ids
    assert result["evidence_pack"]["sources"][0]["unit_id"].startswith("project_amber:quest:1:en:detail:unit:")


def test_project_amber_v2_investigate_returns_candidate_and_pinned_evidence(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    reader = ProjectAmberV2SourceReader(db_path)
    store = EvidenceStore.open(db_path)
    evidence = reader.pin_unit_evidence(
        "project_amber:quest:1:ko:detail:unit:1",
        0,
        3,
        role="supports",
        note="Irminsul source",
    )
    assert evidence is not None
    saved = store.append(evidence)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.investigate("Irminsul", language="en", content_type="quest", limit=1, include_textmap=False)

    assert result["candidate_evidence"][0]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"
    assert result["candidate_evidence"][0]["document_id"] == "project_amber:quest:1:en:detail"
    assert result["candidate_evidence"][0]["suggested_role"] == "context"
    assert result["candidate_evidence"][0]["confirmed"] is False
    assert result["counter_candidates"] == []
    assert result["translation_note_candidates"] == []
    assert result["pinned_evidence"][0]["evidence_id"] == saved["record"]["evidence_id"]
    assert result["evidence_store"]["workspace_id"] == "default"


def test_project_amber_v2_search_engine_warns_when_category_is_ignored(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    engine = ProjectAmberV2SearchEngine(db_path)

    result = engine.search("Irminsul", language="en", content_type="quest", category="archive", limit=1)

    assert result["warnings"][0]["code"] == "category_filter_ignored"
    assert result["results"][0]["canonical_id"] == "project_amber:quest:1"


def test_project_amber_v2_search_engine_reports_missing_db(tmp_path: Path) -> None:
    missing_db = tmp_path / "missing.sqlite3"

    with pytest.raises(FileNotFoundError, match="build_project_amber_v2"):
        ProjectAmberV2SearchEngine(missing_db)


def test_lore_search_engine_cli_defaults_search_to_v2(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "lore_search_engine.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "search",
            "Irminsul",
            "--db",
            str(db_path),
            "--language",
            "en",
            "--content-type",
            "quest",
            "--limit",
            "1",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["engine"]["db_version"] == "v2"
    assert output["results"][0]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"


def test_lore_search_engine_cli_defaults_investigate_to_v2(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "lore_search_engine.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "investigate",
            "Irminsul",
            "--db",
            str(db_path),
            "--language",
            "en",
            "--content-type",
            "quest",
            "--limit",
            "1",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    output = json.loads(completed.stdout)
    assert output["engine"]["db_version"] == "v2"
    assert output["evidence_pack"]["sources"][0]["unit_id"] == "project_amber:quest:1:en:detail:unit:0"


def test_search_lore_cli_defaults_to_v2(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "scripts" / "search_lore.py"

    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "Irminsul",
            "--db",
            str(db_path),
            "--language",
            "en",
            "--content-type",
            "quest",
            "--limit",
            "1",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    first_row = json.loads(completed.stdout.splitlines()[0])
    assert first_row["unit_id"] == "project_amber:quest:1:en:detail:unit:0"


def test_lore_search_engine_cli_selects_legacy_v1(monkeypatch: pytest.MonkeyPatch) -> None:
    cli = load_lore_search_engine_cli_module()
    sentinel = object()

    def open_v1(root: Path) -> object:
        return sentinel

    def open_v2(root: Path) -> object:
        raise AssertionError("v2 engine should not be opened")

    monkeypatch.setattr(cli.LoreSearchEngine, "open", open_v1)
    monkeypatch.setattr(cli.ProjectAmberV2SearchEngine, "open", open_v2)

    assert cli.open_developer_search_engine(Path("."), "v1", "legacy.sqlite3") is sentinel


def test_package_cli_source_reader_workflow(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    base = [sys.executable, "-m", "genshin_lore_db", "--root", str(db_path)]
    env = module_subprocess_env()

    window = subprocess.run(
        [
            *base,
            "read-window",
            "project_amber:quest:1:ko:detail:unit:1",
            "--before",
            "1",
            "--after",
            "0",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert window.returncode == 0, window.stderr
    window_output = json.loads(window.stdout)
    assert window_output["center_unit_id"] == "project_amber:quest:1:ko:detail:unit:1"
    assert [row["unit_id"] for row in window_output["before"]] == ["project_amber:quest:1:ko:detail:unit:0"]

    missing = subprocess.run(
        [*base, "read-window", "missing-unit", "--json"],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert missing.returncode == 2
    assert json.loads(missing.stdout)["error"]["code"] == "unit_not_found"

    document = subprocess.run(
        [*base, "read-document", "project_amber:quest:1:ko:detail", "--max-units", "2", "--json"],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert document.returncode == 0, document.stderr
    document_output = json.loads(document.stdout)
    assert document_output["unit_count"] == 4
    assert len(document_output["units"]) == 2

    section = subprocess.run(
        [*base, "read-section", "project_amber:quest:1:ko:detail:section:0", "--no-units", "--json"],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert section.returncode == 0, section.stderr
    section_output = json.loads(section.stdout)
    assert section_output["unit_count"] == 4
    assert "units" not in section_output

    parallel = subprocess.run(
        [
            *base,
            "read-parallel",
            "project_amber:quest:1:ko:detail:unit:0",
            "--languages",
            "ko,en,ja",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert parallel.returncode == 0, parallel.stderr
    parallel_output = json.loads(parallel.stdout)
    assert [block["found"] for block in parallel_output["blocks"]] == [True, True, False]

    search = subprocess.run(
        [
            *base,
            "search",
            "Irminsul",
            "--language",
            "en",
            "--content-type",
            "quest",
            "--limit",
            "1",
            "--with-window",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert search.returncode == 0, search.stderr
    search_output = json.loads(search.stdout)
    assert search_output["results"][0]["source_window"]["center_unit_id"] == "project_amber:quest:1:en:detail:unit:0"


def test_package_cli_pins_and_browses_evidence(tmp_path: Path) -> None:
    _, db_path = build_tiny_v2_fixture(tmp_path)
    base = [sys.executable, "-m", "genshin_lore_db", "--root", str(db_path)]
    env = module_subprocess_env()

    pin = subprocess.run(
        [
            *base,
            "pin-evidence",
            "--unit-id",
            "project_amber:quest:1:ko:detail:unit:1",
            "--start",
            "0",
            "--end",
            "3",
            "--role",
            "supports",
            "--note",
            "Irminsul source",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert pin.returncode == 0, pin.stderr
    pin_output = json.loads(pin.stdout)
    assert pin_output["created"] is True
    assert pin_output["evidence"]["workspace_id"] == "default"
    assert pin_output["evidence"]["excerpt"] == "세계수"

    duplicate = subprocess.run(
        [
            *base,
            "pin-evidence",
            "--unit-id",
            "project_amber:quest:1:ko:detail:unit:1",
            "--start",
            "0",
            "--end",
            "3",
            "--role",
            "supports",
            "--note",
            "Irminsul source",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert duplicate.returncode == 0, duplicate.stderr
    assert json.loads(duplicate.stdout)["created"] is False

    evidence_id = pin_output["evidence_id"]
    listed = subprocess.run(
        [*base, "evidence", "list", "--role", "supports", "--query", "Irminsul", "--json"],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert listed.returncode == 0, listed.stderr
    listed_output = json.loads(listed.stdout)
    assert listed_output["count"] == 1
    assert listed_output["evidence"][0]["evidence_id"] == evidence_id

    shown = subprocess.run(
        [*base, "evidence", "show", evidence_id, "--json"],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert shown.returncode == 0, shown.stderr
    assert json.loads(shown.stdout)["evidence_id"] == evidence_id

    invalid = subprocess.run(
        [
            *base,
            "pin-evidence",
            "--unit-id",
            "project_amber:quest:1:ko:detail:unit:1",
            "--start",
            "0",
            "--end",
            "3",
            "--role",
            "unknown",
            "--json",
        ],
        capture_output=True,
        encoding="utf-8",
        check=False,
        env=env,
    )
    assert invalid.returncode == 2
    invalid_output = json.loads(invalid.stdout)
    assert invalid_output["error"]["code"] == "command_failed"
    assert "role must be one of" in invalid_output["error"]["message"]


def load_lore_search_engine_cli_module():
    script = Path(__file__).resolve().parents[1] / "scripts" / "lore_search_engine.py"
    spec = importlib.util.spec_from_file_location("lore_search_engine_cli_for_test", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def module_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    src = str(Path(__file__).resolve().parents[1] / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else os.pathsep.join([src, existing])
    return env


def build_tiny_v2_fixture(tmp_path: Path) -> tuple[Path, Path]:
    canonical_root = tmp_path / "data" / "canonical" / "project_amber_v2"
    canonical_root.mkdir(parents=True)
    search_dir = tmp_path / "data" / "processed" / "search_v2"
    search_dir.mkdir(parents=True)
    db_path = search_dir / "project_amber_search.sqlite3"

    items = [
        {
            "canonical_id": "project_amber:quest:1",
            "content_type": "quest",
            "item_id": "1",
            "entity_type": "quest",
            "icon": None,
            "rank": None,
            "route": None,
            "release": None,
            "metadata": {},
        }
    ]
    localizations = [
        localization_row("project_amber:quest:1", "ko", "세계수 테스트"),
        localization_row("project_amber:quest:1", "en", "Irminsul Test"),
    ]
    documents = [
        document_row("project_amber:quest:1:ko:detail", "project_amber:quest:1", "ko", "세계수 테스트"),
        document_row("project_amber:quest:1:en:detail", "project_amber:quest:1", "en", "Irminsul Test"),
    ]
    sections = [
        section_row("project_amber:quest:1:ko:detail:section:0", "project_amber:quest:1:ko:detail", "ko", "도입"),
        section_row("project_amber:quest:1:en:detail:section:0", "project_amber:quest:1:en:detail", "en", "Intro"),
    ]
    text_units = [
        unit_row(
            "project_amber:quest:1:ko:detail:unit:0",
            "project_amber:quest:1:ko:detail",
            "project_amber:quest:1:ko:detail:section:0",
            "ko",
            0,
            "세계수",
        ),
        unit_row(
            "project_amber:quest:1:ko:detail:unit:1",
            "project_amber:quest:1:ko:detail",
            "project_amber:quest:1:ko:detail:section:0",
            "ko",
            1,
            "세계수는 기억을 기록한다.",
        ),
        unit_row(
            "project_amber:quest:1:ko:detail:unit:2",
            "project_amber:quest:1:ko:detail",
            "project_amber:quest:1:ko:detail:section:0",
            "ko",
            2,
            "기억은 이야기의 형태로 남는다.",
        ),
        unit_row(
            "project_amber:quest:1:ko:detail:unit:3",
            "project_amber:quest:1:ko:detail",
            "project_amber:quest:1:ko:detail:section:0",
            "ko",
            3,
            "여행자는 그 기록을 따라간다.",
        ),
        unit_row(
            "project_amber:quest:1:en:detail:unit:0",
            "project_amber:quest:1:en:detail",
            "project_amber:quest:1:en:detail:section:0",
            "en",
            0,
            "Irminsul",
        ),
        unit_row(
            "project_amber:quest:1:en:detail:unit:1",
            "project_amber:quest:1:en:detail",
            "project_amber:quest:1:en:detail:section:0",
            "en",
            1,
            "Irminsul records memories.",
        ),
        unit_row(
            "project_amber:quest:1:en:detail:unit:2",
            "project_amber:quest:1:en:detail",
            "project_amber:quest:1:en:detail:section:0",
            "en",
            2,
            "Memories remain as stories.",
        ),
        unit_row(
            "project_amber:quest:1:en:detail:unit:3",
            "project_amber:quest:1:en:detail",
            "project_amber:quest:1:en:detail:section:0",
            "en",
            3,
            "Travelers follow those records.",
        ),
    ]
    relations = [
        {
            "relation_id": "quest_has_section:project_amber:quest:1:project_amber:quest:1:ko:detail:section:0",
            "source_id": "project_amber:quest:1",
            "target_id": "project_amber:quest:1:ko:detail:section:0",
            "relation_type": "quest_has_section",
            "source": "project_amber",
            "metadata": {},
        }
    ]
    entity_names = [
        {
            "canonical_id": "project_amber:quest:1",
            "entity_type": "quest",
            "language": "ko",
            "name": "세계수 테스트",
            "aliases": [],
            "source": "project_amber",
        }
    ]
    textmap_entries = [
        {
            "textmap_id": "1",
            "language": "ko",
            "language_label": "Korean",
            "text": "세계수",
            "text_hash": "textmap-hash",
            "source": "dimbreath_textmap",
            "source_url": None,
            "raw_ref": None,
            "metadata": {},
        }
    ]

    rows_by_file = {
        "items.jsonl": items,
        "localizations.jsonl": localizations,
        "documents.jsonl": documents,
        "sections.jsonl": sections,
        "text_units.jsonl": text_units,
        "relations.jsonl": relations,
        "entity_names.jsonl": entity_names,
        "textmap_entries.jsonl": textmap_entries,
    }
    for filename, rows in rows_by_file.items():
        write_jsonl(canonical_root / filename, rows)

    report = {
        "counts": {
            "items": len(items),
            "localizations": len(localizations),
            "documents": len(documents),
            "sections": len(sections),
            "text_units": len(text_units),
            "relations": len(relations),
            "entity_names": len(entity_names),
            "textmap_entries": len(textmap_entries),
        }
    }
    write_json(canonical_root / "build_report.json", report)
    build_sqlite(db_path, items, localizations, documents, sections, text_units, relations, textmap_entries)
    return canonical_root, db_path


def build_sqlite(
    db_path: Path,
    items: list[dict[str, object]],
    localizations: list[dict[str, object]],
    documents: list[dict[str, object]],
    sections: list[dict[str, object]],
    text_units: list[dict[str, object]],
    relations: list[dict[str, object]],
    textmap_entries: list[dict[str, object]],
) -> None:
    conn = sqlite3.connect(db_path)
    create_v2_schema(conn)
    conn.executemany(
        """
        INSERT INTO items (
            canonical_id, content_type, item_id, entity_type, icon, rank, route, release, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["canonical_id"],
                row["content_type"],
                row["item_id"],
                row["entity_type"],
                row["icon"],
                row["rank"],
                row["route"],
                row["release"],
                stable_json_dumps(row["metadata"]),
            )
            for row in items
        ],
    )
    conn.executemany(
        """
        INSERT INTO localizations (
            canonical_id, language, language_label, title, description, chapter_num, chapter_title,
            route, source, source_url, raw_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["canonical_id"],
                row["language"],
                row["language_label"],
                row["title"],
                row["description"],
                row["chapter_num"],
                row["chapter_title"],
                row["route"],
                row["source"],
                row["source_url"],
                row["raw_ref"],
                stable_json_dumps(row["metadata"]),
            )
            for row in localizations
        ],
    )
    conn.executemany(
        """
        INSERT INTO documents (
            document_id, canonical_id, language, language_label, content_type, document_kind,
            title, text, text_hash, source, source_url, officialness, raw_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["document_id"],
                row["canonical_id"],
                row["language"],
                row["language_label"],
                row["content_type"],
                row["document_kind"],
                row["title"],
                row["text"],
                row["text_hash"],
                row["source"],
                row["source_url"],
                row["officialness"],
                stable_json_dumps(row["raw_refs"]),
                stable_json_dumps(row["metadata"]),
            )
            for row in documents
        ],
    )
    conn.executemany(
        """
        INSERT INTO sections (
            section_id, document_id, canonical_id, language, language_label, content_type,
            section_type, title, ordinal, text, text_hash, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["section_id"],
                row["document_id"],
                row["canonical_id"],
                row["language"],
                row["language_label"],
                row["content_type"],
                row["section_type"],
                row["title"],
                row["ordinal"],
                row["text"],
                row["text_hash"],
                stable_json_dumps(row["metadata"]),
            )
            for row in sections
        ],
    )
    conn.executemany(
        """
        INSERT INTO text_units (
            unit_id, document_id, canonical_id, section_id, language, language_label, content_type,
            document_kind, title, speaker, ordinal, text, text_hash, source, source_url,
            raw_refs_json, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["unit_id"],
                row["document_id"],
                row["canonical_id"],
                row["section_id"],
                row["language"],
                row["language_label"],
                row["content_type"],
                row["document_kind"],
                row["title"],
                row["speaker"],
                row["ordinal"],
                row["text"],
                row["text_hash"],
                row["source"],
                row["source_url"],
                stable_json_dumps(row["raw_refs"]),
                stable_json_dumps(row["metadata"]),
            )
            for row in text_units
        ],
    )
    conn.executemany(
        """
        INSERT INTO relations (relation_id, source_id, target_id, relation_type, source, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["relation_id"],
                row["source_id"],
                row["target_id"],
                row["relation_type"],
                row["source"],
                stable_json_dumps(row["metadata"]),
            )
            for row in relations
        ],
    )
    conn.executemany(
        """
        INSERT INTO textmap_entries (
            textmap_id, language, language_label, text, text_hash, source, source_url, raw_ref, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                row["textmap_id"],
                row["language"],
                row["language_label"],
                row["text"],
                row["text_hash"],
                row["source"],
                row["source_url"],
                row["raw_ref"],
                stable_json_dumps(row["metadata"]),
            )
            for row in textmap_entries
        ],
    )
    conn.commit()
    populate_v2_fts(conn)
    conn.commit()
    conn.close()


def localization_row(canonical_id: str, language: str, title: str) -> dict[str, object]:
    return {
        "canonical_id": canonical_id,
        "language": language,
        "language_label": "Korean" if language == "ko" else "English",
        "title": title,
        "description": None,
        "chapter_num": None,
        "chapter_title": None,
        "route": None,
        "source": "project_amber",
        "source_url": None,
        "raw_ref": None,
        "metadata": {},
    }


def document_row(document_id: str, canonical_id: str, language: str, title: str) -> dict[str, object]:
    text = (
        "세계수\n세계수는 기억을 기록한다.\n기억은 이야기의 형태로 남는다.\n여행자는 그 기록을 따라간다."
        if language == "ko"
        else "Irminsul"
    )
    return {
        "document_id": document_id,
        "canonical_id": canonical_id,
        "language": language,
        "language_label": "Korean" if language == "ko" else "English",
        "content_type": "quest",
        "document_kind": "detail",
        "title": title,
        "text": text,
        "text_hash": f"{language}-doc-hash",
        "source": "project_amber",
        "source_url": None,
        "officialness": "official",
        "raw_refs": [],
        "metadata": {},
    }


def section_row(section_id: str, document_id: str, language: str, title: str) -> dict[str, object]:
    return {
        "section_id": section_id,
        "document_id": document_id,
        "canonical_id": "project_amber:quest:1",
        "language": language,
        "language_label": "Korean" if language == "ko" else "English",
        "content_type": "quest",
        "section_type": "story",
        "title": title,
        "ordinal": 0,
        "text": title,
        "text_hash": f"{language}-section-hash",
        "metadata": {},
    }


def unit_row(unit_id: str, document_id: str, section_id: str, language: str, ordinal: int, text: str) -> dict[str, object]:
    return {
        "unit_id": unit_id,
        "document_id": document_id,
        "canonical_id": "project_amber:quest:1",
        "section_id": section_id,
        "language": language,
        "language_label": "Korean" if language == "ko" else "English",
        "content_type": "quest",
        "document_kind": "detail",
        "title": "세계수 테스트" if language == "ko" else "Irminsul Test",
        "speaker": None,
        "ordinal": ordinal,
        "text": text,
        "text_hash": f"{language}-unit-{ordinal}-hash",
        "source": "project_amber",
        "source_url": None,
        "raw_refs": [],
        "metadata": {},
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows) + "\n", encoding="utf-8")


def write_json(path: Path, value: dict[str, object]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
