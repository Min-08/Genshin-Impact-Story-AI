# 프로젝트 구조

이 문서는 v0.6 이후 코드와 문서의 기준 배치를 정리합니다. 목표는 데이터 산출물, 파이프라인 코드, 검색엔진 코드, 연구 문서를 섞지 않는 것입니다.

## 최상위 구조

```text
config/
  sources.json
  search_engine_manual_concepts.json
  search_evaluation_set.json

docs/
  PROJECT_VISION.md
  ARCHITECTURE.md
  DATA_PIPELINE.md
  SEARCH_ENGINE.md
  ANSWER_ROUTING_DESIGN.md
  ROADMAP.md
  PROJECT_STRUCTURE.md
  research/

schemas/
  evidence_pack.schema.json
  search_evaluation_case.schema.json

scripts/
  crawl_*.py
  build_*.py
  search_lore.py
  lore_search_engine.py
  eval_search_engine.py

src/genshin_lore_db/
  cli.py
  io.py
  http.py
  models.py
  normalize.py
  project_amber.py
  project_amber_deep.py
  dimbreath.py
  rag_assets.py
  pipeline/
  search_engine/

data/
  raw/
  processed/
  canonical/
```

## 코드 책임

`scripts/`는 개발자가 실행하는 얇은 진입점입니다. 큰 로직은 `src/genshin_lore_db/` 아래에 둡니다.

`src/genshin_lore_db/pipeline/`은 RAW 또는 canonical 데이터를 다른 산출물로 변환하는 빌드 파이프라인을 둡니다. v0.6 기준 Project Amber v2 빌더는 여기로 이동했습니다.

```text
src/genshin_lore_db/pipeline/
  __init__.py
  project_amber_v2.py
```

`src/genshin_lore_db/project_amber_v2.py`는 기존 import 호환을 위한 래퍼입니다. 새 코드는 `genshin_lore_db.pipeline.project_amber_v2`를 사용합니다.

`src/genshin_lore_db/search_engine/`은 질의 라우팅, 별칭, Evidence Pack, 검색엔진 코어처럼 검색 시점에 필요한 코드를 둡니다.

`src/genshin_lore_db/project_amber.py`, `project_amber_deep.py`, `dimbreath.py`는 현재 수집기 역할을 유지합니다. 이후 정리 단계에서 `sources/project_amber/`, `sources/textmap/`으로 옮길 후보입니다.

## 데이터 책임

`data/raw/`는 수집 원문 보관 영역입니다. 파이프라인은 이 영역을 수정하지 않습니다.

`data/processed/project_amber_readable_v2/`는 사람이 읽기 쉬운 Project Amber v2 복사본입니다. 폴더명은 `book`, `quest`, `avatar` 같은 안정적인 코드명을 사용하고, 파일명에는 ID와 언어별 제목을 함께 둡니다.

`data/canonical/project_amber_v2/`는 v0.6 이후 메인 canonical DB입니다.

```text
items.jsonl
localizations.jsonl
documents.jsonl
sections.jsonl
text_units.jsonl
relations.jsonl
entity_names.jsonl
textmap_entries.jsonl
build_report.json
```

`data/processed/search_v2/project_amber_search.sqlite3`는 v2 개발자 검색 DB입니다. 검색 결과는 문서뿐 아니라 `text_unit_id`까지 추적할 수 있어야 합니다.

기존 `data/canonical/`, `data/processed/search/`, `data/processed/project_amber/`는 v1/legacy 산출물로 유지합니다.

## 문서 책임

루트 README는 빠른 안내와 주요 링크만 둡니다. 세부 설명은 `docs/`로 분리합니다.

```text
docs/PROJECT_VISION.md      # 프로젝트 목적
docs/ARCHITECTURE.md        # 시스템 계층과 목표 구조
docs/DATA_PIPELINE.md       # 수집, RAW, processed, canonical, index
docs/SEARCH_ENGINE.md       # 검색엔진과 Evidence Pack
docs/ANSWER_ROUTING_DESIGN.md # 질문 수준별 답변 라우팅과 AI 사용 계약
docs/ROADMAP.md             # 버전별 목표
docs/PROJECT_STRUCTURE.md   # 코드/문서/데이터 배치 기준
docs/research/              # 논의 로그와 평가 메모
```

## 정리 원칙

- 기존 v1 산출물과 v2 산출물은 명확히 분리합니다.
- RAW, processed, canonical, index를 같은 폴더에 섞지 않습니다.
- 새 빌드 로직은 가능하면 `pipeline/` 아래에 둡니다.
- 새 검색 로직은 가능하면 `search_engine/` 아래에 둡니다.
- 대용량 생성 데이터는 GitHub에 올리지 않는 것을 기본값으로 둡니다.
- import 호환이 필요한 기존 모듈은 얇은 래퍼로 남기고, 새 코드만 새 경로를 사용합니다.
