# 원신 스토리 연구 AI

원신 공식 텍스트를 기반으로 스토리 추측과 세계관 연구를 돕는 개발자용 데이터베이스/검색엔진 프로젝트입니다.

목표는 단순한 검색 챗봇이 아닙니다. Project Amber 전체 덤프와 다국어 TextMap을 정규화하고, 한중일영 공식 텍스트를 함께 탐색하면서 인물, 장소, 개념, 모티프, 번역 차이, 반례 후보를 연결하는 연구용 기반 시스템을 만드는 것입니다.

현재 버전은 **v0.6**입니다. 데이터 수집과 정규화, SQLite 기반 검색엔진 코어, 기본 Query Router, Evidence Pack v0.5, 검색 평가셋이 구축되어 있습니다. v0.6에서는 Project Amber 전용 v2 DB 구조와 readable v2 산출물을 추가했습니다. 벡터 검색, 모티프 인덱스, 그래프 검색, 워크스페이스 메모리, 웹 UI는 아직 개발 전입니다.

## 문서

- [프로젝트 비전](docs/PROJECT_VISION.md): 이 프로젝트가 지향하는 최종 형태
- [시스템 아키텍처](docs/ARCHITECTURE.md): 전체 계층, 현재 구현 상태, 향후 구성
- [데이터 파이프라인](docs/DATA_PIPELINE.md): 수집, RAW 보존, 정규화, 산출물 구조
- [검색엔진](docs/SEARCH_ENGINE.md): 현재 검색 코어, 질의 확장, Evidence Pack
- [답변 라우팅 설계](docs/ANSWER_ROUTING_DESIGN.md): `basic_lookup`, `summary`, `analysis`, `research`별 검색/AI 처리 계약
- [프로젝트 구조](docs/PROJECT_STRUCTURE.md): 코드, 문서, 데이터 산출물 배치 기준
- [로드맵](docs/ROADMAP.md): v0.5, v1.0 조건과 개발 순서

## 현재 구현된 것

- Project Amber 데이터 수집
- Project Amber 상세 페이지 보강 수집
- Dimbreath/AnimeGameData TextMap 수집
- 사람이 읽을 수 있는 Project Amber 전처리 데이터 생성
- canonical 문서/청크/엔티티/출처 JSONL 생성
- RAG용 문서와 청크 생성
- SQLite FTS5 기반 검색 DB 생성
- 다국어 엔티티/별칭 인덱스 생성
- 개발자용 `search` / `investigate` CLI
- 개발자용 `route` CLI
- 검색 평가셋과 평가 리포트 생성
- Evidence Pack v0.5 스키마
- LLM 호출 전 단계의 프롬프트 패키지 생성
- Project Amber v2 canonical/readable/search DB 병행 생성
- 책/성유물/무기/캐릭터/재료 deep 데이터를 `_보충 데이터`가 아니라 항목 하위 문서로 승격
- 로컬 Ollama Qwen3 기반 정답형 QA 초안 생성

현재 생성된 주요 데이터 규모는 다음과 같습니다.

```text
문서: 79,773개
청크: 149,824개
TextMap 항목: 959,510개
엔티티/개념 그룹: 17,447개
별칭: 73,327개
```

## 빠른 사용

이미 데이터와 인덱스가 생성되어 있다면 다음처럼 검색엔진을 바로 확인할 수 있습니다.

```powershell
python scripts/lore_search_engine.py search "천리" --limit 5
python scripts/lore_search_engine.py search "Khaenri'ah" --limit 5
python scripts/lore_search_engine.py route "세계수와 기억 조작 연결 가능성"
python scripts/lore_search_engine.py investigate "페이몬의 정체와 천리 관련 근거" --limit 12
python scripts/lore_chat.py
python scripts/eval_search_engine.py
python scripts/eval_answer_engine.py --fail-under
```

Project Amber v2 DB를 만든 뒤 text unit 단위 검색을 확인할 수 있습니다.

```powershell
python scripts/build_project_amber_v2.py
python scripts/search_lore.py --db-version v2 "민들레밭의 여우" --language ko --content-type book --limit 5
python scripts/search_lore.py --db-version v2 "니벨룽겐" --language ko --limit 5
```

정답형 질문은 Project Amber RAW에서 facts JSON을 만든 뒤 템플릿 답변을 생성하고, 선택적으로 로컬 Qwen3가 문장만 다듬습니다. LLM은 사실 생성기가 아니라 facts rewriter이며, 검증에 실패하면 템플릿 답변으로 되돌아갑니다.

```powershell
python scripts/lore_search_engine.py answer "절연의 기치 효과 알려줘" --no-llm --text
python scripts/lore_search_engine.py answer "푸리나 기본정보" --no-llm --text
python scripts/lore_search_engine.py answer "안개를 가르는 회광 정보" --no-llm --text

python scripts/setup_local_llm.py --install --model qwen3:4b-instruct
python scripts/lore_search_engine.py answer "절연의 기치 효과 알려줘" --text
python scripts/eval_answer_engine.py --llm --fail-under
```

터미널에서 계속 질문을 던지며 테스트하려면 대화형 QA를 실행합니다. 기본값은 라우팅 ON, 로컬 Qwen3 ON입니다.

```powershell
python scripts/lore_chat.py
python scripts/lore_search_engine.py chat
.\lore_chat.cmd
```

데이터를 처음부터 다시 만들 때의 기본 흐름은 다음과 같습니다.

```powershell
python scripts/crawl_project_amber.py
python scripts/crawl_project_amber_deep.py
python scripts/crawl_project_amber_extras.py
python scripts/crawl_dimbreath_textmap.py

python scripts/build_project_amber_processed.py
python scripts/build_project_amber_v2.py
python scripts/build_canonical.py
python scripts/build_rag_assets.py
python scripts/build_entity_aliases.py
python scripts/build_search_engine_assets.py
```

수집과 인덱스 생성에는 시간이 걸리고, 생성 데이터는 매우 커질 수 있습니다.

## 저장소 구조

```text
config/
  search_engine_manual_concepts.json
  answer_evaluation_set.json
  search_evaluation_set.json
  sources.json

scripts/
  crawl_project_amber.py
  crawl_project_amber_deep.py
  crawl_project_amber_extras.py
  crawl_dimbreath_textmap.py
  build_project_amber_processed.py
  build_project_amber_v2.py
  build_canonical.py
  build_rag_assets.py
  build_entity_aliases.py
  build_search_engine_assets.py
  lore_search_engine.py
  lore_chat.py
  setup_local_llm.py
  setup_local_llama.py
  eval_answer_engine.py
  eval_search_engine.py

schemas/
  answer_evaluation_case.schema.json
  evidence_pack.schema.json
  search_evaluation_case.schema.json

src/genshin_lore_db/
  cli.py
  io.py
  http.py
  models.py
  project_amber.py
  project_amber_deep.py
  dimbreath.py
  normalize.py
  rag_assets.py
  pipeline/
    project_amber_v2.py
  search_engine/

docs/
  PROJECT_VISION.md
  ARCHITECTURE.md
  DATA_PIPELINE.md
  SEARCH_ENGINE.md
  ANSWER_ROUTING_DESIGN.md
  PROJECT_STRUCTURE.md
  ROADMAP.md
  research/
```

`data/` 아래의 RAW, canonical, processed, SQLite 인덱스는 재생성 가능한 산출물로 취급합니다. GitHub에는 원칙적으로 코드, 설정, 문서만 올리고 대용량 생성 데이터는 제외하는 방향이 안전합니다. 세부 배치 기준은 [프로젝트 구조](docs/PROJECT_STRUCTURE.md)를 따릅니다.

## 기본 원칙

- RAW 데이터는 수정하지 않습니다.
- 공식 원문, 자동 추출 관계, AI 가설, 외부 자료, 자체 추론을 구분합니다.
- 한국어 질문이 들어와도 중국어 간체, 일본어, 영어 표현까지 함께 검색할 수 있게 합니다.
- LLM이 직접 DB를 마음대로 탐색하게 두지 않고, 검색엔진이 Evidence Pack을 만들어 제공합니다.
- 검색 품질은 평가셋으로 반복 측정합니다.
- 최종 목표는 검색 결과를 요약하는 챗봇이 아니라, 근거와 반례를 들고 여러 가설을 비교하는 원신 스토리 연구 에이전트입니다.

## 외부 데이터 주의

이 프로젝트는 Project Amber와 Dimbreath/AnimeGameData 계열 TextMap을 수집 대상으로 사용합니다. 저장소에 대용량 원본 데이터나 재배포가 애매한 산출물을 그대로 포함하지 않는 것을 권장합니다. 각 데이터 출처의 이용 조건을 별도로 확인해야 합니다.
