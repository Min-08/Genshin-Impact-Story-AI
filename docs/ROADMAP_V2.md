# Roadmap v2

작성일: 2026-06-28  
최신화: 2026-06-28

이 문서는 현재 코드와 평가 결과를 기준으로 프로젝트의 실제 진행도와 다음 개발 순서를 정리한다.

## 1. 현재 결론

현재 프로젝트는 다음 단계다.

```text
Developer-facing Retrieval Core MVP
+ Project Amber v2 corpus/search DB
+ deterministic Basic Lookup QA
+ AnswerPlan route contract v0.1
+ requested_style 기반 default/detail/brief 답변 제어
+ ConversationState v0.1
+ Local LLM rewriter/semantic parser 보조 경로
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
Long-term memory product
```

핵심 원칙은 그대로다.

```text
LLM은 질문 의미와 표현을 돕는다.
hard guard, DB resolver, validator가 route safety와 factual correctness를 결정한다.
```

## 2. 검증된 현재 상태

2026-06-28 기준 확인 결과:

```text
python -m pytest
- 43 passed

python scripts/eval_answer_engine.py --fail-under
- cases: 34
- route_match: 1.0
- requested_style_match: 1.0
- context_used_match: 1.0
- validation_ok: 1.0
- case_passed: 1.0

python scripts/eval_answer_engine.py --llm --fail-under
- cases: 34
- route_match: 1.0
- requested_style_match: 1.0
- context_used_match: 1.0
- validation_ok: 1.0
- case_passed: 1.0

python scripts/eval_search_engine.py
- cases: 18
- canonical_recall_at_k: 1.0
- concept_recall: 1.0
- route_accuracy: 1.0
- MRR: 0.9722

python scripts/eval_project_amber_v2.py
- cases: 10
- canonical_recall_at_k: 1.0
- content_type_recall: 1.0
- language_recall: 1.0
- required_fragment_recall: 1.0
- MRR: 1.0

python scripts/audit_project_amber_v2.py
- ok: true
- items: 10,786
- documents: 48,490
- sections: 55,276
- text_units: 2,475,551
- textmap_entries: 959,510
- search DB integrity_check: ok
```

## 3. 완료된 v0.6.x 항목

### v0.6.1 - deterministic basic_lookup 안정화

완료:

```text
LLM 없이도 answer evaluation 100% 통과
캐릭터/무기/성유물 basic_lookup 템플릿과 validator 계약 정리
인사말 guard 유지
unsupported guide/meta request의 basic_lookup 승격 차단
```

### v0.6.2 - Route Contract / Semantic Merge Hardening

완료:

```text
AnswerPlan v0.1 추가
route, intent, entities, requested_style, detail_level, context metadata 고정
hard guard 우선순위 고정
command/greeting guard → unsupported strategy guard → deterministic entity resolver → LLM parser → fallback router
추천/티어/세팅/나선비경/공략은 unsupported + guide_or_meta_request로 고정
summary/analysis/research writer 미구현 상태는 route_not_implemented로 보존
```

### v0.6.3 - Answer Style Controller

완료:

```text
requested_style 도입: brief, default, detail, raw, evidence, analysis, research
requested_format은 paragraph/bullet/table 용도로 유지
푸리나에 대해서 요약해줘 → basic_lookup + character_basic_info + brief
푸리나 스토리 요약해줘 → summary + character_story_summary + route_not_implemented
무기 default 답변은 R1 기준 효과만 출력
R1부터 R5까지/제련별/자세히/전체 요청은 detail로 R1~R5 출력
```

### v0.6.4 - ConversationState v0.1

완료:

```text
세션 한정 ConversationState 추가
terminal.py 루프에서 상태 유지
평가셋 history로 대화 상태 재현
스토리도 알려줘 → 직전 active_entity 기반 summary intent
더 자세히 → 직전 active_entity 기반 detail style
근거는? → 직전 sources metadata 기반 최소 evidence 응답
```

## 4. 현재 완성도 판단

| 영역 | 현재 단계 기준 | 최종 목표 기준 | 판단 |
|---|---:|---:|---|
| Project Amber 수집/정규화 | 85% | 55% | v2 산출물과 audit가 통과한다. 외부 공식 자료 확장은 별도 과제다. |
| Project Amber v2 DB | 80% | 60% | 248만 text unit과 SQLite 검색 DB가 안정적으로 작동한다. |
| 기본 검색엔진 | 75% | 45% | FTS, alias, concept seed, 평가셋이 통과한다. 벡터/모티프/그래프는 아직 없다. |
| Query Router / AnswerPlan | 80% | 45% | hard guard와 DB resolver 우선 정책이 고정됐다. |
| Basic Lookup QA | 80% | 45% | no-LLM/LLM 평가가 모두 통과한다. |
| Answer Style Controller | 55% | 30% | default/detail/brief/evidence의 최소 계약은 구현됐다. 자연어 writer는 보수적이다. |
| ConversationState | 35% | 20% | 세션 한정 v0.1이 있다. 장기 메모리나 API orchestration은 없다. |
| Local LLM | 40% | 20% | rewriter와 semantic parser 보조 역할이다. 최종 판단 권한은 없다. |
| Source Reader | 45% | 30% | v0.1 구현과 테스트가 있다. Evidence Pack/AnswerPlan 통합은 다음 과제다. |
| Evidence Pack | 50% | 30% | investigate용 묶음은 있다. claim 모델과 span 고정은 부족하다. |
| Summary route | 20% | 10% | route/intent는 잡지만 writer는 없다. |
| Analysis route | 20% | 15% | 검색 기반은 있으나 claim 기반 writer가 없다. |
| Research route | 10% | 10% | 설계 단계다. |
| API/Web UI/Memory | 0-5% | 0-5% | 아직 시작하지 않는 것이 맞다. |
| 테스트/평가 | 75% | 40% | 단위 테스트와 no-LLM/LLM answer gate가 있다. route별 전용 평가셋은 더 필요하다. |

## 5. 남은 핵심 문제

### 5.1 Source Reader와 Evidence Pack 통합

Source Reader는 미구현이 아니라 v0.1 구현 상태다. 남은 것은 AnswerPlan과 Evidence Pack에 연결해 `근거는?`을 단순 metadata 표시가 아니라 실제 원문 window/pin으로 확장하는 일이다.

필요 작업:

```text
검색 hit의 unit_id/document_id를 read_window/read_document로 확장
last_sources metadata를 source_reader unit/window로 연결
Evidence Pack에 pinned span 저장
answer validation에서 source_level과 span presence 확인
```

### 5.2 Summary Scope와 Writer

`푸리나 스토리 요약해줘`, `수메르 마신임무 요약해줘`는 route metadata까지는 잡지만 답변은 unsupported로 끝난다.

필요 작업:

```text
summary scope resolver
book volume, quest chain, avatar story 순서 복원
ordered source units 생성
summary writer와 summary 평가셋
```

### 5.3 Analysis/Research Writer

현재 analysis/research는 검색과 Evidence Pack의 기반만 있다. 최종 답변에는 다음 구조가 필요하다.

```text
공식 원문에서 확인되는 것
간접적으로 연결되는 것
가능한 해석
반례 또는 약점
아직 단정할 수 없는 부분
```

이를 위해 claim 모델, evidence pin, source_level validator가 필요하다.

## 6. 다음 개발 순서

### v0.7 - Source Reader / Evidence Pack Integration

목표:

```text
검색 hit와 직전 답변 source metadata에서 원문 window, section, document, evidence pin을 만들 수 있다.
```

완료 기준:

```text
근거는? 이 raw_ref metadata만 보여주는 대신 원문 window와 source pin을 보여준다.
Evidence Pack이 단순 hit 목록이 아니라 pin 가능한 근거 묶음이 된다.
```

### v0.7.5 - Summary Scope와 Summary Index

목표:

```text
특정 책, 책 시리즈, 퀘스트 체인, 캐릭터 스토리를 범위 손실 없이 요약할 준비를 한다.
```

완료 기준:

```text
일월 과거사 요약, 민들레밭의 여우 내용, 수메르 마신임무 요약이 먼저 범위를 확정한다.
writer가 없어도 ordered source units는 검증 가능해야 한다.
```

### v0.8 - Analysis Writer

목표:

```text
근거 기반 claim 답변을 생성한다.
```

완료 기준:

```text
천리와 셀레스티아 관계, 운명의 베틀 의미, 파네스와 네 그림자 근거 같은 질문에
공식 근거, 간접 연결, 가능한 해석, 약점을 분리해 답한다.
```

### v0.9 - Research Loop v1

목표:

```text
하나의 연구 질문을 여러 가설과 반례 후보로 나누어 탐색한다.
```

완료 기준:

```text
최소 2개 가설, 지지 근거, 약점, 현재 신뢰도, 다음 조사 방향을 분리한다.
```

### v0.9.5 - Retrieval Expansion

도입 후보:

```text
Vector Search
Motif Index
Similar Passage Index
Translation Diff Index
Co-occurrence Index
Graph Search
```

이 기능들은 research loop의 필요가 명확해진 뒤 붙인다.

### v1.0 - Research Assistant MVP

목표:

```text
API, conversation orchestrator, source viewer, workspace memory, web UI를 갖춘 대화형 연구 보조 도구.
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

## 8. 버전별 마일스톤 요약

| 버전 | 이름 | 상태 | 핵심 완료 조건 |
|---|---|---|---|
| v0.6.1 | Basic Lookup Hardening | 완료 | no-LLM/LLM answer eval 모두 통과 |
| v0.6.2 | Route Contract / Semantic Merge Hardening | 완료 | unsupported 오분류 차단, AnswerPlan metadata 고정 |
| v0.6.3 | Answer Style Controller | 완료 | brief/default/detail/evidence 최소 정책 통과 |
| v0.6.4 | ConversationState v0.1 | 완료 | history 평가와 터미널 후속 질문 처리 |
| v0.7 | Source Reader Integration | 다음 | window/section/document/pin 연결 |
| v0.7.5 | Summary Scope | 예정 | 책/퀘스트/스토리 범위 확정과 ordered units |
| v0.8 | Analysis Writer | 예정 | claim과 source_level을 가진 분석 답변 |
| v0.9 | Research Loop v1 | 예정 | 가설/근거/반례/신뢰도 분리 |
| v0.9.5 | Retrieval Expansion | 예정 | vector, motif, similar, diff, graph 도입 |
| v1.0 | Research Assistant MVP | 예정 | API, conversation, source viewer, memory |

## 9. 최종 판단

현재 병목은 LLM 성능이 아니라 다음 세 가지다.

```text
1. Source Reader/Evidence Pack을 AnswerPlan과 연결하기
2. Summary/Analysis writer에 들어갈 source scope와 claim contract 만들기
3. research loop를 평가 가능한 작은 단계로 나누기
```

v0.6.x의 route/QA 안정화는 통과했다. 다음부터는 더 많은 기능을 붙이는 것보다, 답변이 어떤 source span과 claim에 기대는지 고정하는 방향으로 가야 한다.
