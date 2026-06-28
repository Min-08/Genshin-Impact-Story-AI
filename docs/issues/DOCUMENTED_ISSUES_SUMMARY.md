# 기존 문서 기반 문제점 모음

이 문서는 `docs/`에 이미 적혀 있는 문제점, 한계, 리스크, 미구현 항목만 한곳에 모은 요약이다. 원문 문서는 수정하지 않고, 추적하기 쉽도록 출처를 함께 남긴다.

## 1. v0.6.x에서 정리된 구현 품질 문제와 남은 후속 과제

### 1.1 LLM 출력의 필수 필드 검증 부족

- 문제: LLM rewriter가 `draft_answer`에 있던 필수 정보를 `final_answer`에서 누락해도 validator가 통과할 수 있다.
- 예: 캐릭터 답변에서 `돌파 보너스` 같은 항목이 빠져도 `validation.ok=true`가 될 수 있다.
- 영향: `basic_lookup` 답변이 정형 facts를 잃어도 정상 답변처럼 보인다.
- 상태: v0.6.2~v0.6.4에서 style-aware required fragment 검증과 LLM fallback은 강화됐다. claim-level semantic validator는 후속 과제다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 7.1

### 1.2 무기 제련 효과 표현이 오해를 만들 수 있음

- 문제: 무기 효과가 `1재련 효과`처럼 출력되면, 사용자가 효과가 1재련에 고정된 것처럼 이해할 수 있다.
- 영향: 제련 단계별 수치 변화가 있는 무기 설명에서 UX와 정확성이 떨어진다.
- 상태: v0.6.3에서 default는 R1 기준 효과와 detail 안내를 출력하고, detail 요청에서 R1~R5를 출력하도록 정리됐다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 7.2

### 1.3 캐릭터 facts가 기본 프로필 중심으로 부족함

- 문제: 현재 `character_basic_info`는 이름, 등급, 원소, 무기, 지역, 생일, 칭호, 소개, 운명의 자리 이름, CV, 돌파 보너스 중심이다.
- 부족한 항목: 별자리 C1-C6 효과, 전투 특성, 패시브 특성, 캐릭터 스토리 연결, 음성/대사 연결, 관련 임무/문서 연결.
- 주의: 모든 정보를 기본정보 답변에 항상 출력하면 안 되고, facts는 넓게 만들되 route/intent별 출력 범위를 나눠야 한다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 7.3

### 1.4 basic_lookup 주변 품질 항목이 아직 약함

- 문제 묶음: validator 누락, facts extractor 누락, `basic_lookup` 출력 오류, LLM fallback 문제, 테스트 부족.
- 영향: 현재 실제로 구현된 기능의 정확도와 안전성에 직접 영향을 준다.
- 상태: v0.6.1~v0.6.4에서 no-LLM/LLM answer evaluation은 모두 100% 통과한다. 남은 품질 과제는 Source Reader/Evidence Pack 통합 이후 claim/source validator로 옮겨간다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 11.1

### 1.5 route와 QA 동작 불일치 이슈

- 문제: `route=analysis`인데 `intent=character_basic_info`처럼 표시/실행 계층이 어긋날 수 있다.
- 추가 문제: 일반 인사말 `안녕`이 캐릭터 대사 검색 hit를 통해 말라니 기본정보로 답변되는 사례가 있다.
- 상태: v0.6.2에서 AnswerPlan과 hard guard를 추가해 이번 평가셋 범위의 route/intent mismatch, greeting 오탐, unsupported guide/meta 승격 문제를 막았다.
- 상세 기록: `docs/issues/ROUTING_QA_ISSUES.md`

## 2. 현재 검색엔진 한계

### 2.1 검색 방식과 인덱스가 아직 MVP 수준

- 없는 것: 벡터 검색, 모티프 인덱스, Translation Diff Index, Similar Passage Index, Co-occurrence Index, Graph Search, Workspace Memory, 실제 LLM 답변 생성.
- 영향: 현재 시스템은 `오프라인 검색 MVP + 하이브리드 검색 초안`에 가깝다.
- 출처: `docs/ROADMAP.md` 현재 위치, `docs/SEARCH_ENGINE.md` 현재 한계

### 2.2 Query Router가 기본 휴리스틱 중심

- 문제: 라우터가 아직 규칙/휴리스틱 초안이다.
- 영향: 질의 표현이 조금만 바뀌어도 의도와 route가 어긋날 수 있다.
- 관련 강화 방향: Query Router 정확도 개선, Exact Lookup 강화, Source 조회 구조 정리.
- 출처: `docs/ARCHITECTURE.md` 현재 구현 상태, `docs/ROADMAP.md` v0.6 조건

### 2.3 반례 검색과 관계 탐색이 아직 약함

- 문제: 반례 검색은 후보 그룹 수준이고, 진짜 논리적 반례 탐지는 어렵다.
- 영향: `research` 질문에서 가설의 약점과 대안 가설을 충분히 찾지 못할 수 있다.
- 출처: `docs/SEARCH_ENGINE.md` 현재 한계, `docs/research/RESEARCH_AGENT_ADDITIONAL_DISCUSSION.md` 한계

### 2.4 요약 색인만으로는 작은 단서가 손실될 수 있음

- 문제: Summary Index는 넓은 정찰에는 유용하지만 원문 압축 과정에서 작은 떡밥, 상징 표현, 반복 모티프, 번역 차이, 반례성 문장, 한 번만 등장하는 핵심 단서를 잃을 수 있다.
- 영향: 연구형 질문에서 사용자가 찾고 싶은 미세 단서가 누락될 수 있다.
- 출처: `docs/research/DATA_AND_RETRIEVAL_VISION.md` 9

## 3. 라우트와 답변 생성 미구현 항목

### 3.1 summary/analysis/research writer가 아직 없음

- 상태: `answer CLI`는 `basic_lookup` 중심이고, `summary route writer`, `analysis route writer`는 없음, `research route`는 구조만 있다.
- 영향: 라우터가 route를 분류해도 실제 route별 답변 생성 품질은 아직 제한적이다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 구현 상태 표

### 3.2 Source Reader와 Summary Index가 다음 단계로 남아 있음

- 문제: Source Reader v0.1은 구현되어 있지만, 검색 hit/직전 답변 source metadata를 원문 window와 evidence pin으로 확장하고 핵심 주장을 원문 span에 고정하는 구조는 아직 다음 단계다.
- 영향: 분석/연구 답변에서 인용 가능한 근거 span 추적이 제한된다.
- 출처: `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 구현 상태 표, `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 권장 구현 순서

### 3.3 API, 웹 UI, 대화 오케스트레이터는 아직 후순위

- 상태: API server, tool-calling agent, planner, web UI는 아직 없음 또는 후순위다.
- 주의: 현재 프로젝트는 사용자가 바로 쓰는 완성형 대화 AI가 아니라 developer-facing retrieval core에 가깝다.
- 출처: `docs/ARCHITECTURE.md`, `docs/research/CURRENT_STATUS_AND_STAGE_DECISIONS.md` 7.4 및 11.3

## 4. Validator와 답변 안전성 리스크

### 4.1 숫자/이름 검사만으로는 부족함

- 문제: 작은 LLM은 숫자나 이름을 바꾸지 않아도 오류를 만들 수 있다.
- 가능한 오류: 약한 표현을 단정으로 바꿈, 관계 방향을 뒤집음, 원문에 없는 원인-결과 추가, 부정문을 긍정문처럼 바꿈, 조건 누락.
- 필요한 검증 대상: `allowed_claims`, `forbidden_claims`, `source_fields`, `required_qualifiers`, 관계 방향, 부정/긍정 유지, 조건 누락 여부.
- 출처: `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 4.2, `docs/research/RESEARCH_AGENT_ADDITIONAL_DISCUSSION.md` 6

### 4.2 연구형 답변은 evidence span 검증이 핵심

- 문제: 연구형 답변에서 최종 결론 자체를 자동 검증하기는 어렵다.
- 현실적 방향: 각 주장에 evidence span이 붙어 있는지 확인하고, 공식 원문/간접 연결/AI 가설/반례/신뢰도를 분리한다.
- 출처: `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 4.2, `docs/research/RESEARCH_AGENT_ADDITIONAL_DISCUSSION.md` 연구형 답변 구조

### 4.3 실패 처리 정책이 실제 구현과 연결되어야 함

- 정리된 실패 상황: 엔티티 후보 다중, exact lookup 실패, summary scope 불명확, Evidence Pack 품질 낮음, LLM rewrite validator 실패, research budget 초과, counter evidence 검색 실패.
- 문제: 정책 문서가 있어도 실제 answer layer에서 일관되게 적용되지 않으면 UX가 흔들린다.
- 출처: `docs/ANSWER_ROUTING_DESIGN.md` 16

## 5. 연구형 기능 설계 리스크

### 5.1 너무 빨리 멀티 에이전트화될 위험

- 문제: 초기부터 Research Supervisor, Planner Agent, Retrieval Agent, Reader Agent, Discovery Agent, Counter Agent, Hypothesis Agent, Synthesizer Agent를 독립 agent로 나누면 복잡도가 급격히 커진다.
- 권장 방향: 처음에는 하나의 research loop 안에서 planner/reader/discovery/counter/synthesizer를 역할 함수로 구현한다.
- 출처: `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 4.1

### 5.2 Research Memory 오염 위험

- 위험: AI가 만든 가설을 공식 사실처럼 재사용, 사용자 선호를 공식 근거보다 강하게 반영, 반박된 가설을 계속 사용, 오래된 버전 텍스트를 최신 근거처럼 사용.
- 필요한 구분: 공식 원문, 자동 추출 관계, 사용자 가설, AI 추론, 확인 필요, 반박됨, 폐기됨.
- 출처: `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 4.3, `docs/research/RESEARCH_AGENT_ADDITIONAL_DISCUSSION.md` 한계

### 5.3 Discovery Agent는 novelty와 noise를 같이 만든다

- 문제: 예상 밖 연결을 찾는 데 유용하지만 관련 없는 문서까지 끌어올 위험이 있다.
- 필요한 상태: candidate, accepted, rejected, needs_review.
- 점수는 단순 relevance가 아니라 novelty, source_quality, noise_penalty를 함께 봐야 한다.
- 출처: `docs/research/RESEARCH_AGENT_DISCUSSION_EVALUATION.md` 4.4

## 6. 데이터와 출처 리스크

### 6.1 Project Amber만으로는 최종 연구 AI에 부족함

- 문제: 최종 목표인 대화형 원신 스토리 연구 AI에는 게임 내부 텍스트 외에도 공식 영상, 공식 웹 문서, 공식 맵, 이벤트 페이지, PV, 방송, 공간 배치, 외부 비교 자료가 필요하다.
- 영향: DB 밖 정보와 새 버전 텍스트는 수집/업데이트 전까지 모른다.
- 출처: `docs/research/DATA_AND_RETRIEVAL_VISION.md`, `docs/research/DB_EXPANSION_AND_RESEARCH_DATA_VISION.md`

### 6.2 외부 지식과 커뮤니티 자료는 공식 근거와 섞이면 위험함

- 문제: 외부 비교틀은 공식 설정의 증거가 아니며, 커뮤니티/공략 데이터는 유용하지만 공식 근거와 섞이면 위험하다.
- 방향: 외부 지식은 별도 검증 대상으로 두고, 커뮤니티 자료는 후순위와 낮은 출처 등급으로 관리한다.
- 출처: `docs/research/DATA_AND_RETRIEVAL_VISION.md` 13-14

### 6.3 raw data 공개 리스크

- 문제: 공식 웹, YouTube, 맵, 커뮤니티 자료는 약관/저작권 문제가 있을 수 있다.
- 방향: 공개 저장소에는 parser, schema, docs만 두고 raw dump나 full transcript는 로컬/개인 DB에 보관한다.
- 출처: `docs/research/DATA_AND_RETRIEVAL_VISION.md` 28.1, `docs/PROJECT_STRUCTURE.md` 데이터 공개 정책

## 7. 우선순위 요약

v0.6.x에서 우선 정리된 문제:

```text
1. LLM required-field validator 강화
2. basic_lookup 출력 오류 정리
3. 무기 제련 효과 표현 개선
4. route/intent 불일치와 인사말 오탐 방지
5. unsupported guide/meta request hard guard
6. 관련 테스트/평가 케이스 추가
```

다음 단계에서 구현할 문제:

```text
1. Source Reader v0.1과 Evidence Pack 통합
2. Summary Scope/Index
3. summary/analysis/research route별 writer
4. Evidence Span 고정
5. 벡터 검색
6. 모티프/공출현/유사문장/번역차이 인덱스
7. 반례 검색 강화
```

후순위 또는 서비스화 단계:

```text
1. API server
2. tool-calling agent
3. Conversation Orchestrator
4. Workspace Memory
5. 웹 UI
```
