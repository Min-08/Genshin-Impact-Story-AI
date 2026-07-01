# 프로젝트 구조

Status: reference document for repository layout and generated artifacts.

이 문서는 현재 코드, 데이터 산출물, 문서, 테스트의 기준 배치를 정리합니다. 기준은 `PROJECT_VISION`, `ARCHITECTURE`, `DATA_PIPELINE`, `SEARCH_ENGINE`, `ANSWER_ROUTING_DESIGN`, `ROADMAP`, `docs/research/*`의 현재 결론입니다.

현재 단계는 **v0.8.5 Claude-Code Lessons Architecture Alignment 문서화 완료 / v0.8.6 준비**입니다. 웹 UI, API 서버, tool-calling agent, Conversation Orchestrator는 아직 구현 단계가 아닙니다.

## 최상위 구조

```text
config/
  sources.json
  search_engine_manual_concepts.json
  answer_evaluation_set.json
  search_evaluation_set.json

docs/
  README.md
  PROJECT_VISION.md
  ARCHITECTURE.md
  DATA_PIPELINE.md
  DB_GROUNDED_QUERY_UNDERSTANDING.md
  SEARCH_ENGINE.md
  ANSWER_ROUTING_DESIGN.md
  ROADMAP.md
  PROJECT_STRUCTURE.md
  design/
  implementation/
  research/

schemas/
  answer_evaluation_case.schema.json
  evidence_pack.schema.json
  search_evaluation_case.schema.json

scripts/
  crawl_*.py
  fill_*.py
  build_*.py
  search_lore.py
  lore_search_engine.py
  lore_chat.py
  setup_local_llm.py
  setup_local_llama.py
  eval_answer_engine.py
  eval_search_engine.py

src/genshin_lore_db/
  cli.py
  io.py
  http.py
  models.py
  normalize.py
  project_amber.py
  project_amber_deep.py
  project_amber_v2.py
  dimbreath.py
  rag_assets.py
  pipeline/
  search_engine/

tests/
  test_local_llm.py
  test_qa.py
  test_router.py
  test_terminal.py

data/
  raw/
  processed/
  canonical/
  logs/

lore_chat.cmd
lore_chat.ps1
pyproject.toml
README.md
```

## 코드 책임

`scripts/`는 개발자가 직접 실행하는 얇은 진입점입니다. 큰 로직은 `src/genshin_lore_db/` 아래에 둡니다.

현재 스크립트 책임:

```text
crawl_project_amber*.py         Project Amber 수집
crawl_dimbreath_textmap.py      TextMap 수집
crawl_genshin_data_readable.py  보조 readable 수집
fill_project_amber_*.py         Project Amber 상세/보강 병렬 보충
build_project_amber_processed.py
build_project_amber_v2.py
build_canonical.py
build_rag_assets.py
build_entity_aliases.py
build_search_engine_assets.py
search_lore.py                  v1/v2 DB 빠른 검색 확인
lore_search_engine.py           route/search/investigate/answer/chat 개발자 CLI
lore_chat.py                    대화형 QA 터미널
setup_local_llm.py              Ollama 로컬 QA 모델 준비
setup_local_llama.py            이전 이름 호환용 설치 스크립트
eval_answer_engine.py           정답형 QA 평가셋 실행
eval_search_engine.py           검색 평가셋 실행
```

루트의 `lore_chat.cmd`, `lore_chat.ps1`는 Windows 터미널에서 대화형 QA를 바로 실행하기 위한 편의 런처입니다.

## 패키지 책임

`src/genshin_lore_db/`의 루트 모듈은 공통 유틸과 현재 수집기/빌더 호환 계층을 둡니다.

```text
cli.py                 공통 CLI 보조
io.py                  JSON/JSONL 입출력
http.py                HTTP 수집 보조
models.py              공통 데이터 모델
normalize.py           텍스트 정규화
project_amber.py       Project Amber 기본 수집기
project_amber_deep.py  Project Amber 상세 수집기
project_amber_v2.py    v2 빌더 import 호환 래퍼
dimbreath.py           TextMap 수집기
rag_assets.py          RAG 문서/청크 산출물 생성
```

`src/genshin_lore_db/pipeline/`은 RAW 또는 canonical 데이터를 다른 산출물로 변환하는 빌드 파이프라인을 둡니다.

```text
src/genshin_lore_db/pipeline/
  __init__.py
  project_amber_v2.py
```

v0.6 기준 Project Amber v2 canonical/readable/search DB 빌더는 `pipeline/project_amber_v2.py`가 기준입니다. 기존 `src/genshin_lore_db/project_amber_v2.py`는 import 호환용 래퍼로 유지합니다.

## 검색엔진 책임

`src/genshin_lore_db/search_engine/`은 검색 시점에 필요한 코드를 둡니다.

```text
aliases.py     엔티티/별칭 인덱스 생성과 alias 정규화
answer_evaluation.py 정답형 QA 평가셋 실행과 지표 계산
engine.py      search/investigate 코어, 검색 DB 생성 보조
evidence.py    Evidence Pack 생성
evidence_store.py JSONL evidence pin 저장소
evaluation.py  검색 평가셋 실행과 지표 계산
llm.py         investigate용 LLM 프롬프트 패키지 생성
local_llm.py   Ollama 로컬 LLM 호출과 오류/fallback 정보
qa.py          basic_lookup 정답형 QA, facts 추출, 템플릿, validator
router.py      basic_lookup/summary/analysis/research 휴리스틱 라우터
terminal.py    대화형 QA 터미널 루프
vector.py      벡터 검색 인터페이스 자리
```

현재 `basic_lookup` 정답형 QA는 `search_engine/qa.py`에 있습니다. `ANSWER_ROUTING_DESIGN.md`는 향후 별도 `answer_engine/` 계층을 권장하지만, 지금 단계에서는 아직 분리하지 않습니다.

현재 로컬 LLM의 역할은 `facts → draft_answer`를 자연스러운 한국어로 다듬는 rewriter입니다. 사실 판단은 Project Amber v2 DB와 RAW JSON, 그리고 validator가 담당합니다. 기본 Ollama 모델은 `qwen3:4b-instruct`입니다.

## 데이터 책임

`data/raw/`는 수집 원문 보관 영역입니다. 파이프라인은 이 영역을 직접 수정하지 않는 것을 원칙으로 합니다.

```text
data/raw/
  project_amber/
  dimbreath_textmap/
  genshin_data_readable/
```

`data/processed/`는 사람이 읽기 쉬운 복사본, 검색 DB, 평가/품질 산출물 등 재생성 가능한 산출물을 둡니다.

```text
data/processed/
  project_amber/
  project_amber_readable_v2/
  rag/
  entities/
  search/
  search_v2/
  search_engine/
  quality/
  schema/
```

`data/processed/project_amber_readable_v2/`는 사람이 읽기 쉬운 Project Amber v2 복사본입니다. 폴더명은 `book`, `quest`, `avatar`, `weapon`, `reliquary` 같은 안정적인 코드명을 사용하고, 파일명에는 ID와 언어별 제목을 함께 둡니다.

`data/canonical/project_amber_v2/`는 v0.6 이후 Project Amber v2의 메인 canonical 산출물입니다.

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

`data/workspaces/<workspace_id>/evidence_pins.jsonl`은 v0.8 evidence pin 저장소입니다. 기본 workspace는 `default`이고, 같은 `evidence_id`는 중복 저장하지 않습니다.

기존 `data/canonical/*.jsonl`, `data/processed/search/`, `data/processed/project_amber/`는 v1/legacy 산출물로 유지합니다.

## 문서 책임

루트 `README.md`는 빠른 안내와 주요 링크만 둡니다. 고정된 설계 기준은 상위 `docs/`에 둡니다.

```text
docs/PROJECT_VISION.md          프로젝트 목적과 최종 정의
docs/ARCHITECTURE.md            시스템 계층과 현재/미래 구현 상태
docs/DATA_PIPELINE.md           수집, RAW, processed, canonical, index 구조
docs/SEARCH_ENGINE.md           검색엔진, Evidence Pack, 정답형 QA, 로컬 Qwen3 사용법
docs/ANSWER_ROUTING_DESIGN.md   질문 수준별 route, answer contract, 후속 answer_engine 설계
docs/ROADMAP.md                 v0.5~v1.0 단계별 목표
docs/PROJECT_STRUCTURE.md       코드/문서/데이터 배치 기준
docs/design/                    v0.8.5+ architecture contracts and future-stage designs
docs/implementation/            실행 로드맵과 implementation notes
```

`docs/research/`는 실행 코드나 고정 스펙이 아니라 연구성 문서와 판단 기록을 둡니다.

```text
docs/research/README.md
docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md
docs/research/CONVERSATIONAL_AI_VISION.md
docs/research/DATA_AND_RETRIEVAL_VISION.md
docs/research/DB_EXPANSION_AND_RESEARCH_DATA_VISION.md
docs/research/RESEARCH_AGENT_ADDITIONAL_DISCUSSION.md
docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md
```

연구 문서의 결론은 현재 단계 판단에 참고하되, 실제 구현 기준은 상위 `docs/`와 현재 코드 상태를 우선합니다.

## 현재 단계와 다음 배치

현재 구현 단계:

```text
v0.8
- JSONL evidence pin store
- pin-evidence/evidence list/evidence show CLI
- investigate candidate_evidence/pinned_evidence 출력
- Source Reader span pin과 evidence store 연결
- basic_lookup 정답형 QA 안정화 유지

v0.8.3
- DB-Grounded Query Understanding / Meaning Search
- query_understanding Candidate Meaning Pack diagnostics on route/answer output
- strong/weak/unsafe candidate policy before basic_lookup execution

v0.8.5
- docs/design/LLM_RUNTIME_PROFILES.md
- docs/design/CONTEXT_ASSEMBLY_DESIGN.md
- docs/design/AGENTIC_LOOP_DESIGN.md
- docs/design/RESEARCH_LOOP_DESIGN.md
- docs/design/STREAMING_VISIBLE_THINKING_DESIGN.md
- docs/design/WRITER_FOUNDATION_DESIGN.md
```

다음 단계에서 추가될 가능성이 높은 배치:

```text
config/
  llm_profiles.json
  execution_modes.json
  router_models.json
  reasoner_models.json
  writer_models.json
  model_runtime_defaults.json

schemas/
  semantic_state.schema.json
  turn_context.schema.json
  prompt_package.schema.json

src/genshin_lore_db/llm/
  runtime_profile.py
  profile_loader.py
  provider_config.py
  runtime_selector.py

src/genshin_lore_db/context_engine/
  turn_context.py
  context_assembler.py
  context_blocks.py
  db_map_context.py
  search_policy_context.py
  answer_policy_context.py
  evidence_policy_context.py
  prompt_package_builder.py
```

v0.9 이후 writer 단계에서 추가될 가능성이 높은 배치:

```text
src/genshin_lore_db/answer_engine/
  router_contracts.py
  planner.py
  lookup.py
  summary.py
  analysis.py
  research.py
  prompts.py
  validators.py
  schemas.py
  writers.py

src/genshin_lore_db/search_engine/scouts/
  summary_scout.py
  raw_keyword_scout.py
  semantic_scout.py
  motif_scout.py
  graph_scout.py
  translation_scout.py
  counter_scout.py
  external_frame_scout.py
```

장기적으로 데이터 확장 단계에서 고려할 배치:

```text
src/genshin_lore_db/ingest/
src/genshin_lore_db/canonical/
src/genshin_lore_db/index/

data/raw/official_web/
data/raw/official_youtube/
data/raw/official_map/
data/raw/comparative_frames/
data/raw/community_optional/

data/canonical/documents/
data/canonical/media/
data/canonical/map/
data/canonical/entities/
data/canonical/summaries/
data/canonical/discovery/
data/canonical/relations/
data/canonical/hypotheses/
```

이 배치는 아직 구현된 현재 구조가 아니라 `DATA_AND_RETRIEVAL_VISION.md`와 연구 문서의 후속 설계 후보입니다. 지금 당장 빈 디렉터리를 만들지는 않습니다.

## 테스트 책임

`tests/`는 현재 검색/QA 코어의 회귀 테스트를 둡니다.

```text
test_local_llm.py  기본 Ollama 모델명, Qwen thinking 후처리
test_qa.py         facts 추출, draft, validator
test_router.py     basic_lookup 라우팅 신호
test_terminal.py   대화형 터미널 상태 표시
```

테스트 설정은 `pyproject.toml`의 `tool.pytest.ini_options`에 둡니다. 대용량 `data/`를 pytest가 스캔하지 않도록 `testpaths = ["tests"]`를 유지합니다.

## 공개/비공개 원칙

공개 저장소에 올릴 기본 대상:

```text
src/
scripts/
config/
docs/
schemas/
tests/
README.md
pyproject.toml
```

로컬 또는 별도 배포 대상으로 보는 대상:

```text
data/raw/
data/canonical/
data/processed/
SQLite 인덱스
대용량 JSONL 산출물
Ollama 모델 캐시
```

공식 웹, YouTube, 맵, 커뮤니티 자료는 약관/저작권 문제가 있을 수 있으므로 parser, schema, docs만 공개하고 raw dump나 full transcript는 로컬/개인 DB에 보관합니다.

## 정리 원칙

- 기존 v1 산출물과 v2 산출물은 명확히 분리합니다.
- RAW, processed, canonical, index를 같은 폴더에 섞지 않습니다.
- 새 빌드 로직은 가능하면 `pipeline/` 아래에 둡니다.
- 새 검색 로직은 가능하면 `search_engine/` 아래에 둡니다.
- 정답형 QA가 커지면 `ANSWER_ROUTING_DESIGN.md`의 `answer_engine/` 분리안을 따릅니다.
- Summary/Analysis/Research는 Source Reader와 Evidence Pin이 생긴 뒤 확장합니다.
- 모티프, 그래프, 번역 차이, Multi-Scout, Workspace Memory는 공식 근거와 AI 가설을 분리할 수 있을 때 추가합니다.
- import 호환이 필요한 기존 모듈은 얇은 래퍼로 남기고, 새 코드는 새 기준 경로를 사용합니다.
