# Roadmap v2

작성일: 2026-06-28

이 문서는 기존 `docs/ROADMAP.md`를 대체하기보다, 현재 코드와 평가 결과를 기준으로 프로젝트의 실제 진행도와 다음 개발 순서를 다시 잡기 위한 v2 로드맵이다.

## 1. 현재 결론

현재 프로젝트는 다음 단계로 보는 것이 가장 정확하다.

```text
Developer-facing Retrieval Core MVP
+ Project Amber v2 corpus/search DB
+ Basic Lookup QA
+ Local LLM Rewriter
+ Source Reader v0.1
+ Evidence Pack Prototype
```

아직 다음 단계는 아니다.

```text
Autonomous Research Agent
Full tool-calling LLM system
ChatGPT-like conversational assistant
API-backed product
Web UI product
```

즉 지금 상태는 실패한 완성형 AI가 아니라, 최종 연구 에이전트를 만들기 위한 검색/출처/정형 QA 기반이 상당히 쌓인 상태다. 다만 현재 구현된 `basic_lookup`과 route/QA 경계는 아직 더 단단하게 만들어야 한다.

## 2. 검증된 현재 상태

최근 확인 결과는 다음과 같다.

```text
pytest:
- 35 passed

search evaluation:
- cases: 18
- canonical_recall_at_k: 1.0
- concept_recall: 1.0
- content_type_recall: 1.0
- MRR: 0.9722
- route_accuracy: 1.0

Project Amber v2 search evaluation:
- cases: 10
- canonical_recall_at_k: 1.0
- content_type_recall: 1.0
- language_recall: 1.0
- MRR: 1.0
- required_fragment_recall: 1.0

Project Amber v2 audit:
- ok: true
- items: 10,786
- documents: 48,490
- sections: 55,276
- text_units: 2,475,551
- textmap_entries: 959,510
- search DB integrity_check: ok
```

정답형 QA는 평가 모드에 따라 차이가 있다.

```text
LLM mode answer evaluation:
- cases: 24
- case_passed: 1.0
- validation_ok: 1.0

no-LLM deterministic answer evaluation:
- cases: 24
- route_match: 0.9583
- required_fragments_present: 0.75
- validation_ok: 0.75
- case_passed: 0.7083
```

이 차이는 중요하다. 현재 LLM rewriter가 켜진 경로는 평가를 통과했지만, LLM 없이 템플릿과 validator만으로도 항상 통과하는 상태는 아니다. 최종 제품에서는 LLM이 꺼져도 정형 조회가 맞아야 하므로, v0.6.x의 핵심 과제는 deterministic QA 안정화다.

## 3. 완성도 판단

아래 완성도는 두 기준으로 나눈다.

```text
현재 단계 기준:
v0.6.x 검색 코어와 정형 QA MVP를 얼마나 안정적으로 만족하는가.

최종 목표 기준:
근거와 반례를 비교하는 대화형 연구 에이전트까지 얼마나 왔는가.
```

| 영역 | 현재 단계 기준 | 최종 목표 기준 | 판단 |
|---|---:|---:|---|
| Project Amber 수집/정규화 | 85% | 55% | v1/v2 산출물이 모두 있고 검증도 통과한다. 외부 공식 자료 확장은 아직 별도 과제다. |
| Project Amber v2 DB | 80% | 60% | 248만 text unit과 SQLite 검색 DB가 있고 audit가 통과한다. 문서 체인/관계 의미화는 더 필요하다. |
| 기본 검색엔진 | 75% | 45% | FTS, alias, concept seed, 평가셋은 작동한다. 벡터/모티프/그래프/번역차이는 없다. |
| Query Router | 65% | 35% | 인사말 guard와 exact entity 보정은 개선됐다. 다만 unsupported query의 과한 exact match는 남아 있다. |
| Basic Lookup QA | 65% | 35% | 성유물/무기/캐릭터 기본조회는 된다. no-LLM 평가 실패와 출력 계약 문제가 남아 있다. |
| Local LLM | 40% | 20% | rewriter와 semantic parser 보조 역할이다. planner나 연구 분석가는 아니다. |
| Source Reader | 45% | 30% | `read_unit`, `read_window`, `read_document`, `read_parallel`, evidence pin 초안과 테스트가 있다. route writer와는 아직 연결 전이다. |
| Evidence Pack | 50% | 30% | `investigate`용 묶음은 있다. claim 모델, span 고정, 반례 검증은 부족하다. |
| Summary route | 15% | 10% | 라우팅과 설계는 있으나 실제 summary scope resolver/writer는 아직 없다. |
| Analysis route | 20% | 15% | 검색과 Evidence Pack은 있으나 claim 기반 답변 writer가 없다. |
| Research route | 10% | 10% | 설계는 좋지만 실제 research loop와 hypothesis state는 아직 전이다. |
| API/Web UI/Memory | 0-5% | 0-5% | 아직 시작하지 않는 것이 맞다. 지금 만들면 하부 도구가 부족하다. |
| 테스트/평가 | 65% | 35% | 단위 테스트와 평가셋이 있다. 라우트별 평가셋과 no-LLM 품질 gate가 더 필요하다. |

전체적으로 보면 현재 프로젝트는 v0.6.x 중후반이다. 최종 연구 에이전트 기준으로는 약 25-30% 정도지만, 하부 코어만 놓고 보면 60-70% 정도까지 왔다.

## 4. 이미 해결된 것으로 보이는 항목

기존 이슈 문서에 남아 있지만 현재 코드 기준으로 개선된 항목이 있다.

```text
아야카 단독/기본정보 질의:
- 현재 route=basic_lookup
- intent=character_basic_info

안녕 인사말:
- 현재 route=chitchat
- intent=small_talk
- 캐릭터 대사 검색으로 말라니 기본정보를 답하지 않음

Source Reader:
- 기존 문서에는 미구현으로 적힌 부분이 있지만 현재는 v0.1 구현과 테스트가 있음
```

따라서 다음 문서 정리 때 `docs/issues/ROUTING_QA_ISSUES.md`와 `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md`의 상태를 업데이트해야 한다.

## 5. 아직 남은 핵심 문제

### 5.1 no-LLM basic_lookup 실패

현재 no-LLM 평가에서 캐릭터 기본정보 케이스가 required fragment를 만족하지 못한다.

대표 실패:

```text
푸리나 기본정보
라이덴 쇼군 기본정보
종려 기본정보
나히다 기본정보
벤티 기본정보
호두 기본정보
```

실제 답변에는 의미상 같은 정보가 들어 있지만, 평가 기준은 `원소: 물`, `무기: 한손검`, `지역: 폰타인` 같은 명시적 fragment를 요구한다. 해결 방향은 둘 중 하나다.

```text
1. 템플릿을 평가 계약에 맞춰 더 구조화한다.
2. 평가 fragment를 자연문 템플릿에 맞게 재정의한다.
```

정확도와 유지보수성을 생각하면 1번이 낫다. 정형 조회는 사람이 읽기 좋은 자연문보다 필드가 빠지지 않는 구조가 우선이다.

### 5.2 unsupported query의 과한 exact lookup

`나선비경 티어 알려줘`가 route 단계에서 `basic_lookup`과 weapon entity로 끌려가는 사례가 있다. 최종 답변은 unsupported로 안전하게 끝나지만, route metadata는 부정확하다.

수정 방향:

```text
추천, 티어, 조합, 세팅, 공략, 나선비경 같은 비공식/공략형 intent는 exact entity lookup보다 먼저 unsupported 또는 guide 계열로 분리한다.
exact lookup은 사용자가 특정 공식 DB 항목을 물을 때만 route를 basic_lookup으로 승격한다.
```

### 5.3 LLM 런타임 의존성

Ollama가 켜져 있으면 LLM mode 평가가 통과하지만, 꺼져 있으면 semantic parser는 connection error 후 fallback한다. 이 동작 자체는 맞지만, 품질 gate는 LLM 없이도 통과해야 한다.

정책:

```text
LLM은 품질 개선 장치다.
LLM은 정형 QA correctness의 필수 조건이 되면 안 된다.
```

### 5.4 Evidence Pack에서 실제 답변까지의 간극

현재 `investigate`는 자료 묶음과 프롬프트 패키지를 만들 수 있다. 하지만 사용자가 원하는 것은 결국 다음 구조의 답변이다.

```text
공식 원문에서 확인되는 것
간접적으로 연결되는 것
가능한 해석
반례 또는 약점
아직 단정할 수 없는 부분
```

이를 위해서는 claim 모델, evidence pin, source_level validator가 필요하다.

## 6. 개발 순서

### v0.6.1 - deterministic basic_lookup 안정화

목표:

```text
LLM 없이도 정형 QA가 평가셋을 100% 통과한다.
```

작업:

```text
1. 캐릭터 기본정보 템플릿을 구조화한다.
2. required_fact_fragments와 템플릿 출력 계약을 일치시킨다.
3. `나선비경 티어`, `성유물 추천`, `조합 추천` 같은 unsupported/guide intent를 먼저 차단한다.
4. answer evaluation을 no-LLM과 LLM 둘 다 gate로 둔다.
5. 기존 이슈 문서에서 해결된 항목과 남은 항목을 분리한다.
```

완료 기준:

```text
python -m pytest
python scripts/eval_answer_engine.py --fail-under
python scripts/eval_answer_engine.py --llm --fail-under

위 세 명령이 모두 통과해야 한다.
```

### v0.6.2 - route/intent 계약 정리

목표:

```text
route는 표시용 metadata가 아니라 answer execution plan의 출발점이 된다.
```

작업:

```text
1. RouteDecision에 intent, entities, requested_format, risk_flags, unsupported_reason을 고정한다.
2. QA resolver가 route와 충돌할 때 보정 정책을 명시한다.
3. semantic parser 실패 시 fallback 결과가 deterministic route와 같은 schema를 반환하게 한다.
4. route/intent mismatch 평가 케이스를 추가한다.
```

완료 기준:

```text
route=analysis인데 intent=character_basic_info인 상태가 사라진다.
unsupported query가 엉뚱한 exact entity로 route 승격되지 않는다.
```

### v0.7 - Source Reader 통합

목표:

```text
검색 hit에서 원문 window, section, document, parallel language를 바로 읽고 evidence pin을 만들 수 있다.
```

현재 Source Reader v0.1은 구현되어 있으므로 다음은 통합 작업이다.

작업:

```text
1. `investigate` 결과에서 source_reader next action을 연결한다.
2. 검색 hit의 unit_id/document_id를 read_window로 확장한다.
3. evidence pin을 Evidence Pack source/group에 연결한다.
4. `scripts/read_source.py` CLI 사용 예시를 문서화한다.
5. real DB fixture 또는 샘플 쿼리 기반 테스트를 추가한다.
```

완료 기준:

```text
검색 결과 한 줄에서 원문 전후 문맥과 다국어 병렬 단위를 확인할 수 있다.
Evidence Pack이 단순 hit 목록이 아니라 pin 가능한 근거 묶음이 된다.
```

### v0.7.5 - Summary Scope와 Summary Index

목표:

```text
특정 책, 책 시리즈, 퀘스트 체인, 캐릭터 스토리를 범위 손실 없이 요약할 준비를 한다.
```

작업:

```text
1. summary scope resolver를 만든다.
2. book volume, quest chain, avatar story의 순서를 복원한다.
3. document_summaries와 segment_summaries를 생성한다.
4. summary evidence package를 만든다.
5. summary 평가셋을 별도로 만든다.
```

완료 기준:

```text
`일월 과거사 요약`, `민들레밭의 여우 내용`, `수메르 마신임무 요약`이 범위를 먼저 확정한다.
요약 writer가 없어도 scope와 ordered source units는 검증 가능해야 한다.
```

### v0.8 - Analysis Writer

목표:

```text
단순 검색 결과가 아니라 근거 기반 분석 답변을 생성한다.
```

작업:

```text
1. Claim 모델을 추가한다.
2. claim_type을 direct_fact, inferred_relation, symbolic_interpretation, counterpoint 등으로 나눈다.
3. Evidence Pack과 Source Reader pin을 claim에 연결한다.
4. analysis writer를 만든다.
5. source_level/qualifier validator를 추가한다.
```

완료 기준:

```text
`천리와 셀레스티아 관계`, `운명의 베틀 의미`, `파네스와 네 그림자 근거` 같은 질문에
공식 근거, 간접 연결, 가능한 해석, 약점을 분리해 답한다.
```

### v0.9 - Research Loop v1

목표:

```text
하나의 연구 질문을 여러 가설과 반례 후보로 나누어 탐색한다.
```

처음부터 멀티 에이전트로 나누지 않는다. 하나의 `research_loop()` 안에서 역할 함수로 시작한다.

```text
planner
retriever
reader
discovery
counter_search
synthesizer
validator
```

작업:

```text
1. ResearchPlan 모델을 만든다.
2. hypothesis state를 둔다.
3. counter evidence 검색을 최소 1회 수행한다.
4. discovered concept 후보를 candidate/accepted/rejected로 관리한다.
5. research 평가셋을 만든다.
```

완료 기준:

```text
`페이몬 정체 공식 근거 중심`, `파네스와 천리 동일 가능성` 같은 질문에서
최소 2개 가설, 지지 근거, 약점, 현재 신뢰도, 다음 조사 방향을 분리한다.
```

### v0.9.5 - Retrieval Expansion

목표:

```text
research route가 FTS hit 몇 개에 갇히지 않도록 탐색 채널을 확장한다.
```

작업:

```text
1. Vector Search
2. Motif Index
3. Similar Passage Index
4. Translation Diff Index
5. Co-occurrence Index
6. Graph Search
```

주의:

```text
이 기능들은 research loop의 필요가 명확해진 뒤 붙인다.
지금 바로 모두 만들면 평가 기준 없이 복잡도만 늘어난다.
```

### v1.0 - API, Conversation, Memory, UI

목표:

```text
사용자가 대화형 연구 보조 도구로 쓸 수 있는 상태를 만든다.
```

작업:

```text
1. FastAPI 또는 동등한 Search/Answer API
2. tool schema
3. conversation orchestrator
4. streaming research progress
5. source viewer
6. workspace memory
7. web UI
```

완료 기준:

```text
사용자가 같은 대화에서 lookup, summary, analysis, research를 이어갈 수 있다.
시스템은 공식 근거, 자동 추출 관계, AI 가설, 사용자 메모리를 섞지 않는다.
```

## 7. 당장 하지 말아야 할 것

```text
1. 웹 UI부터 만들기
2. 독립 멀티 에이전트 구조부터 만들기
3. LLM에게 FTS 검색만 주고 research agent라고 부르기
4. 외부 위키/커뮤니티 자료를 공식 근거와 섞기
5. 벡터 검색을 평가셋 없이 붙이기
6. 대용량 raw/generated data를 저장소에 올리기
```

지금 필요한 것은 더 화려한 겉면이 아니라 정형 QA, route 계약, Source Reader 통합, Evidence Pin이다.

## 8. 권장 우선순위

가장 현실적인 다음 작업 순서는 다음이다.

```text
1. no-LLM answer evaluation 100% 통과
2. unsupported/guide intent guard 강화
3. route/intent 계약 정리
4. 해결된 이슈 문서 업데이트
5. Source Reader를 investigate/Evidence Pack에 연결
6. Summary Scope resolver 구현
7. Analysis Claim 모델과 writer 구현
8. Research Loop v1 구현
9. Vector/Motif/Graph/Translation Diff 확장
10. API/Conversation/UI 구현
```

## 9. 버전별 마일스톤 요약

| 버전 | 이름 | 핵심 완료 조건 |
|---|---|---|
| v0.6.1 | Basic Lookup Hardening | no-LLM/LLM answer eval 모두 통과 |
| v0.6.2 | Route Contract | route/intent mismatch와 unsupported 오분류 해소 |
| v0.7 | Source Reader Integration | 검색 hit에서 window/section/document/pin 연결 |
| v0.7.5 | Summary Scope | 책/퀘스트/스토리 범위 확정과 ordered units |
| v0.8 | Analysis Writer | claim과 source_level을 가진 분석 답변 |
| v0.9 | Research Loop v1 | 가설/근거/반례/신뢰도 분리 |
| v0.9.5 | Retrieval Expansion | vector, motif, similar, diff, graph 도입 |
| v1.0 | Research Assistant MVP | API, conversation, source viewer, memory |

## 10. 최종 판단

현재 프로젝트는 데이터 파이프라인과 검색 코어가 생각보다 많이 완성되어 있다. 특히 Project Amber v2, Source Reader v0.1, 평가셋, 정답형 QA까지 들어온 것은 좋은 기반이다.

하지만 다음 단계로 바로 agent나 UI를 만들면 하부 계약이 흔들린다. 지금 병목은 LLM 성능이 아니라 다음 세 가지다.

```text
1. 정형 QA의 deterministic correctness
2. route/intent/execution contract
3. 검색 hit를 원문 근거 span으로 고정하는 Source Reader/Evidence Pin 통합
```

이 세 가지를 먼저 끝내면 summary, analysis, research는 자연스럽게 쌓을 수 있다. 반대로 이 세 가지를 건너뛰면 겉으로는 대화형 AI처럼 보이지만, 실제로는 근거가 약한 검색 결과 요약기가 된다.
