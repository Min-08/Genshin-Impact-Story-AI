# Claude Code Lessons 적용 계획 문서

Status: design / future architecture input for v0.8.5+. It is not an
implementation-complete record.

Current use: v0.8.4 Regression Cleanup and D-Docs documentation cleanup are now
treated as completed prerequisites. Use this document as input for v0.8.5
architecture alignment, with `PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md`
as the PM-approved sequencing source of truth.

프로젝트: **Genshin-Impact-Story-AI**
문서 목적: Claude Code식 agentic loop / context assembly / semantic parser / runtime profiles / research loop / visible thinking 설계를 현재 프로젝트 로드맵에 언제, 어느 범위로 적용할지 정리한다.
작성 시점: v0.8.3 DB-Grounded Query Understanding 구현 후, v0.8.4 Regression Cleanup 진행 중.

---

## 0. 핵심 결론

당시 진행 중이던 **D. v0.8.4 Regression Cleanup**에는 새 설계를 섞지 않는다.

D는 오직 다음을 확인하고 고치는 단계다.

```text
- v0.8.3 Query Understanding 회귀 여부
- QA routing 안정성
- source/evidence follow-up context 오염 여부
- search/investigate fallback 품질
- docs와 실제 동작 불일치
```

Claude Code 대화 덤프에서 논의한 설계는 타당하지만, 바로 D에 구현하면 D의 목적이 흐려진다.

따라서 적용 순서는 다음으로 고정한다.

```text
D. v0.8.4 Regression Cleanup
↓
D-Docs. Documentation Map / Naming Cleanup
↓
v0.8.5 Claude-Code Lessons Architecture Alignment
↓
v0.8.6 Minimal Runtime + Context Foundation
↓
Final v0.8.x Audit
↓
v0.9 Summary / Analysis / Research Writer Foundation
↓
v0.10 Tool Engine / Execution Plan
↓
v0.11 Research Planner / Evidence Judge
↓
v0.12 Agentic Research Loop V1
↓
v0.13 Streaming / Visible Thinking / UI Event Contract
```

한 줄 판단:

```text
지금은 새 agentic loop를 구현할 때가 아니라,
v0.9 writer가 나중에 무너지지 않도록 필요한 계약과 최소 기반만 먼저 깔 때다.
```

---

## 1. 현재 프로젝트 상태

### 1.1 완료된 기반

현재 프로젝트는 다음 기반을 이미 갖추고 있다.

```text
- Project Amber v2 검색 DB
- TextMap 검색
- Source Reader
- Evidence Pack
- Evidence Pin
- strict basic_lookup QA
- QA terminal
- search / investigate CLI
- DB-Grounded Query Understanding v0.8.3
- Candidate Meaning Pack
- lore concept registry
- strong / weak / unsafe match policy
- LLM candidate adjudication fallback
```

즉 현재까지 만든 것은 잘못된 본체가 아니라, 앞으로 LLM 의미파악과 agentic research loop가 사용할 **검색/근거 인프라**다.

### 1.2 아직 시작하지 않은 핵심

아직 본격적으로 시작하지 않은 것은 다음이다.

```text
- full SemanticState schema
- TurnContextAssembler
- LLM runtime profile system
- v0.9 writer
- claim-level validator
- tool engine
- agentic loop
- research planner
- evidence judge
- stop controller
- streaming / visible thinking
- frontend integration
```

따라서 구조 전체를 갈아엎을 필요는 없다.

```text
전체 리팩토링 ❌
기존 구조 위에 meaning/context/runtime 계층 추가 ✅
```

---

## 2. Claude Code에서 가져올 핵심 원칙

Claude Code식 구조에서 바로 가져올 핵심은 다음이다.

```text
초기 컨텍스트 조립
+ LLM의 의미 기반 도구 선택
+ tool_result 누적
+ 재추론
+ 필요할 때까지 반복
```

하지만 이 프로젝트에 그대로 복사하면 안 된다.
원신 lore QA/연구 프로젝트에 맞게 역할을 명시화해야 한다.

---

## 3. Context Assembly의 정확한 의미

### 3.1 Context Assembly는 정답을 고르는 단계가 아니다

Context Assembly는 사용자의 질문에 대한 정답을 직접 내리는 단계가 아니다.

정확히는:

```text
LLM이 올바른 검색/추론 행동을 선택하도록
현재 상황판과 규칙표를 만들어주는 단계
```

즉 TurnContextAssembler는 다음을 하면 안 된다.

```text
파네스 = 천리다
세계수는 역사 자체를 바꾼다
니벨룽겐은 반드시 원초의 용왕이다
```

이런 결론은 Source Reader / Evidence Pack / Reasoner / Validator 이후에만 가능하다.

### 3.2 TurnContextAssembler가 해야 할 일

TurnContextAssembler는 다음 정보를 묶는다.

```text
- 사용자 질문 원문
- normalized query
- Query Understanding 결과
- Candidate Meaning Pack
- selected meaning
- 최근 대화 상태
- active entity / active topic
- source/evidence follow-up 가능 여부
- DB map 요약
- 검색 우선순위
- 답변 정책
- 근거 정책
- 현재 구현 범위 / future-route 정보
```

예상 출력:

```json
{
  "query": "파네스와 천리는 같은 존재야?",
  "semantic_state": {
    "query_type": "relation_compare",
    "answer_mode": "evidence_first",
    "is_followup": false
  },
  "candidate_meaning_pack": {
    "selected": "concept:phanes",
    "candidates": ["concept:phanes", "concept:heavenly_principles"]
  },
  "search_policy": {
    "priority": [
      "exact_lore_concept_alias",
      "official_source_search",
      "book_search",
      "quest_search",
      "dialogue_search",
      "counter_evidence_search"
    ]
  },
  "answer_policy": {
    "must_separate": ["confirmed", "inference", "speculation"],
    "must_include_uncertainty": true,
    "must_not_invent_sources": true
  }
}
```

---

## 4. Small Model Semantic Parser 설계

### 4.1 소형모델은 답변기가 아니다

소형모델은 최종 답변을 쓰는 모델이 아니라, **검색/추론을 시작하기 위한 의미 지도 생성기**로 써야 한다.

```text
사용자 자연어 질문
→ 소형모델 의미파서
→ 구조화된 JSON 의미 상태
→ 검색 / 도구 선택 / 컨텍스트 조립에 사용
→ Reasoner / Writer가 최종 답변
```

### 4.2 역할 분리

```text
Rule-based Preprocessor
  - 명칭 정규화
  - 별칭 매칭
  - 최근 엔티티 관리
  - 명백한 hard guard

Small Model Semantic Parser
  - 질문 의도 분석
  - 관계 / 근거 / 추측 / 요약 / 시간순 분류
  - 생략된 주어 복원
  - 필요한 검색 도구 후보 생성

JSON Validator
  - schema 검증
  - 이상한 엔티티 제거
  - confidence 낮으면 fallback

TurnContextAssembler
  - semantic_state
  - candidate_entities
  - search_policy
  - answer_policy
  - DB map

Main Reasoner / Writer
  - Evidence Pack 해석
  - claim 비교
  - 최종 답변 작성
```

### 4.3 SemanticState 예시

```json
{
  "schema_version": "semantic_state.v0.1",
  "query_type": "relation_compare",
  "answer_mode": "evidence_first",
  "is_followup": false,
  "resolved_question": "파네스와 천리가 같은 존재인지 또는 어떤 관계인지 공식 텍스트 근거로 비교한다.",
  "focus_entities": [
    {
      "name": "파네스",
      "role": "subject",
      "confidence": 0.95
    },
    {
      "name": "천리",
      "role": "comparison_target",
      "confidence": 0.92
    }
  ],
  "related_terms": [
    "셀레스티아",
    "원초의 그분",
    "Heavenly Principles",
    "Primordial One"
  ],
  "required_searches": [
    "lore_concept_lookup",
    "official_source_search",
    "book_search",
    "quest_search",
    "counter_evidence_search"
  ],
  "risk_flags": [
    "speculation_required",
    "canon_conflict_possible"
  ],
  "confidence": 0.86
}
```

### 4.4 적용 시점

SemanticState 자체는 **v0.8.6**에서 최소 schema와 validator만 넣는 것이 좋다.

실제 소형모델 parser는 다음 순서로 확장한다.

```text
v0.8.6
- semantic_state.schema.json
- semantic_state_validator.py
- deterministic SemanticState adapter

v0.9
- writer 입력으로 SemanticState 사용

v0.10+
- local/API semantic parser profile 연결

v0.11+
- research planner 입력으로 확장
```

---

## 5. LLM Runtime Profiles

### 5.1 왜 지금 설계해야 하는가

v0.9 writer부터는 모델 역할이 분리된다.

이때 단순히 `--model qwen3:4b-instruct` 하나만 두면 나중에 반드시 다시 뜯어고치게 된다.

따라서 writer 구현 전에 최소한 다음 역할을 분리해야 한다.

```text
1. Router / Meaning Parser
2. Reasoner / Research Model
3. Writer / Rewriter
4. Validator
```

### 5.2 실행 모드

실행 모드는 다음처럼 나눈다.

```text
deterministic
- router: deterministic
- reasoner: none
- writer: template

local-full
- router: local
- reasoner: local
- writer: local

local-router-api-reasoner
- router: local
- reasoner: API
- writer: API or local

api-router-local-reasoner
- router: API
- reasoner: local
- writer: local

api-full
- router: API
- reasoner: API
- writer: API
```

### 5.3 Config 초안

```text
config/
├─ llm_profiles.json
├─ execution_modes.json
├─ router_models.json
├─ reasoner_models.json
├─ writer_models.json
├─ semantic_router_policy.json
└─ model_runtime_defaults.json
```

### 5.4 CLI 옵션 초안

```powershell
python scripts/lore_chat.py --llm-profile deterministic
python scripts/lore_chat.py --llm-profile local-full
python scripts/lore_chat.py --llm-profile local-router-api-reasoner
python scripts/lore_chat.py --llm-profile api-router-local-reasoner
python scripts/lore_chat.py --llm-profile api-full
```

세부 override:

```powershell
python scripts/lore_chat.py ^
  --router-provider ollama ^
  --router-model qwen3:4b-instruct ^
  --reasoner-provider api ^
  --reasoner-model provider-default-reasoning-model ^
  --writer-provider ollama ^
  --writer-model qwen3:4b-instruct
```

### 5.5 적용 시점

이건 **v0.8.6에서 최소 구현**해야 한다.

다만 실제 API provider 전체 구현은 v0.9 이후로 미뤄도 된다.

v0.8.6 최소 범위:

```text
- config 파일
- profile loader
- validation
- deterministic/local 기본 profile
- CLI option skeleton
```

---

## 6. Research Mode 설계

### 6.1 리서치 모드는 모델을 여러 번 호출하는 것이 정상

Research mode는 한 번의 LLM 호출로 끝내려고 하면 안 된다.

역할별로 분리해야 한다.

```text
Router / 의미파악: 소형 모델 or deterministic
Research planning: 소형 모델 or 중형 모델
검색 실행: 모델 X, 기존 DB 검색엔진
근거 판정: 소형/중형 or API
최종 추론: 큰 모델/API
문장 정리: 소형 모델 or template
검증: deterministic + 필요시 소형 모델
```

예상 호출 수:

```text
basic_lookup: 0~1회
analysis mode: 2~4회
research mode: 4~10회
```

### 6.2 Research Loop 구조

```text
User Query
  ↓
1. Semantic Parser
  ↓
2. Research Planner
  ↓
3. DB Search / Source Reader
  ↓
4. Evidence Judge
  ↓
5. Counter Evidence Search
  ↓
6. Gap Analyzer
  ↓
7. Stop Controller
  ↓
8. Final Reasoner
  ↓
9. Writer / Validator
  ↓
Final Answer
```

### 6.3 ResearchPlan 예시

```json
{
  "research_goal": "파네스와 천리의 관계를 공식 텍스트 근거로 비교한다.",
  "main_entities": ["파네스", "천리", "셀레스티아"],
  "questions": [
    "파네스가 직접 언급되는 원문은 무엇인가?",
    "천리 또는 Heavenly Principles가 언급되는 원문은 무엇인가?",
    "두 개념이 같은 존재라고 볼 직접 근거가 있는가?",
    "반대로 별개로 볼 근거가 있는가?"
  ],
  "search_tasks": [
    {
      "name": "phanes_sources",
      "query": "파네스 원초의 그분 Primordial One",
      "source_types": ["book", "quest", "dialogue"]
    },
    {
      "name": "heavenly_principles_sources",
      "query": "천리 Heavenly Principles 하늘의 질서",
      "source_types": ["quest", "dialogue", "book"]
    }
  ],
  "counter_evidence_targets": [
    "파네스와 천리를 동일시하지 않는 자료",
    "천리가 별도 주체처럼 언급되는 자료"
  ],
  "answer_requirements": [
    "확정 정보와 추측 분리",
    "직접 근거와 간접 근거 분리",
    "반례 또는 불확실성 포함"
  ]
}
```

### 6.4 StopDecision

Claude Code는 tool_use가 있으면 계속하고, 없으면 종료하는 것처럼 보인다.
하지만 이 프로젝트에서는 종료 조건을 명시화해야 한다.

```text
Plan → Search → Judge → GapAnalyze → StopDecision
```

StopDecision 기준:

```text
- 지금 답변 가능한가
- 추가 검색의 기대 정보 이득이 큰가
- 반례 검색을 했는가
- 남은 불확실성이 더 검색으로 해소 가능한가
- 예산/턴 제한에 도달했는가
- 질문 범위를 벗어나고 있는가
```

결과는 세 가지다.

```text
1. Answer
   지금 답할 수 있음

2. Search / Act More
   더 행동하면 정보가 늘어날 가능성이 큼

3. Abstain / Uncertain Answer
   더 행동해도 확정 불가능하거나 범위 밖임
```

### 6.5 적용 시점

Research Loop는 **v0.9 전에 구현하지 않는다.**

적용 순서:

```text
v0.9
- writer foundation
- Evidence Pack 기반 summary/analysis 초안

v0.10
- tool engine / execution plan

v0.11
- research planner / evidence judge / gap analyzer

v0.12
- agentic research loop v1
```

---

## 7. Streaming / Visible Thinking

### 7.1 내부 reasoning을 보여주면 안 된다

보여줘야 하는 것은 내부 chain of thought가 아니라, 사용자용 진행 상태다.

```text
내부 reasoning / tool trace 직접 노출 ❌
사용자용 visible thinking message ✅
```

예시:

```text
파네스와 천리의 관계를 확인하려면 관련 원문을 먼저 살펴봐야겠어요.
파네스와 천리 관련 후보 문서를 찾고 있어요.
관련 원문을 읽고, 확정 정보와 추측을 분리하고 있어요.
근거가 충분한 주장과 불확실한 해석을 나누어 답변을 정리하고 있어요.
```

### 7.2 Phase별 visible thought

```text
Semantic Router
→ 질문의 핵심 개념을 파악하고 있어요.

Candidate Search
→ 관련 엔티티와 원문 후보를 찾고 있어요.

Source Reader
→ 검색된 원문을 읽고 있어요.

Evidence Builder
→ 근거를 묶고 반례가 있는지 확인하고 있어요.

Reasoner
→ 확정된 내용과 추측 가능한 내용을 분리하고 있어요.

Writer
→ 답변을 정리하고 있어요.
```

### 7.3 Backend event schema 초안

```text
run.started
router.started
router.completed
context.started
context.completed
search.started
search.progress
search.completed
source_read.started
source_read.progress
source_read.completed
evidence.started
evidence.completed
reasoning.started
reasoning.delta
reasoning.completed
writing.started
writing.delta
writing.completed
validation.started
validation.completed
run.completed
run.error
```

### 7.4 적용 시점

Streaming / visible thinking은 지금 바로 구현하지 않는다.

```text
v0.10
- backend event schema 초안

v0.11
- tool progress / research trace 연결

v0.12+
- frontend ThinkingStatus / GradientWritingAnswer 연결
```

---

## 8. Documentation Cleanup과의 관계

이 문서를 적용하기 전에 먼저 해야 했던 선행 조건은 D-Docs였다.

```text
D-Docs. Documentation Map / Naming Cleanup
```

이유:

현재 문서가 많고, `ROADMAP.md`, 과거 roadmap-v2 문서, `CODEX_EXECUTION_ROADMAP...` 등이 같은 계층에 있으면 Codex가 어떤 문서를 기준으로 삼아야 하는지 헷갈릴 수 있다.

따라서 v0.8.5 설계 반영 전에 다음을 정리하는 것이 이 문서의 전제였다.

```text
- README.md를 문서 진입점으로 갱신
- docs/README.md 추가
- canonical / reference / implementation record / superseded / issues 분류
- ROADMAP.md를 canonical roadmap으로 명시
- ROADMAP_V2는 implementation notes로 이동/rename
- CODEX_EXECUTION_ROADMAP은 implementation record로 이동
- stale claim 수정
```

---

## 9. 단계별 적용 계획

### D. v0.8.4 Regression Cleanup

목표:

```text
v0.8.3 Query Understanding 이후 회귀 제거
```

범위:

```text
- query_understanding diagnostics
- supported_entity / lore_concept / story_scope
- context inheritance
- source/evidence follow-up
- search/investigate fallback
- LLM unavailable fallback
```

금지:

```text
- TurnContextAssembler 구현
- runtime profile 구현
- writer 구현
- research loop 구현
- streaming 구현
```

---

### D-Docs. Documentation Map / Naming Cleanup

현재 상태: 완료. 현재 문서 지도와 canonical/reference/implementation record
분류는 `docs/README.md`를 기준으로 한다.

목표:

```text
문서 이름과 상태를 정리하고 README에서 어떤 문서를 봐야 하는지 명확히 한다.
```

범위:

```text
- README.md update
- docs/README.md add/update
- docs/implementation/ 디렉터리 생성
- ROADMAP_V2 rename/move
- CODEX_EXECUTION_ROADMAP move
- canonical/reference/superseded 상태 표시
```

금지:

```text
- 문서 삭제
- runtime code 변경
- 새 기능 구현
```

---

### v0.8.5 Claude-Code Lessons Architecture Alignment

목표:

```text
Claude Code 대화 덤프에서 합의한 설계 원칙을 프로젝트 docs/roadmap에 반영한다.
```

산출물:

```text
docs/CONTEXT_ASSEMBLY_DESIGN.md
docs/LLM_RUNTIME_PROFILES.md
docs/AGENTIC_LOOP_DESIGN.md
docs/RESEARCH_LOOP_DESIGN.md
docs/STREAMING_VISIBLE_THINKING_DESIGN.md
```

단, 이 단계는 주로 문서/계약 단계다.

---

### v0.8.6 Minimal Runtime + Context Foundation

목표:

```text
v0.9 writer가 사용할 최소 런타임 계약과 context package를 만든다.
```

산출물:

```text
config/llm_profiles.json
config/execution_modes.json
schemas/semantic_state.schema.json
schemas/turn_context.schema.json
schemas/prompt_package.schema.json
src/genshin_lore_db/llm/profile_loader.py
src/genshin_lore_db/context_engine/context_assembler.py
src/genshin_lore_db/context_engine/prompt_package_builder.py
tests/test_llm_profiles.py
tests/test_context_assembler.py
```

금지:

```text
- full API provider 구현
- agent loop 구현
- research loop 구현
- streaming UI 구현
```

---

### Final v0.8.x Audit

목표:

```text
v0.9 시작 가능 여부 판정
```

체크리스트:

```text
- D 회귀 정리 완료
- 문서 상태 정리 완료
- Claude Code lessons docs 반영 완료
- minimal runtime/context foundation 완료
- README가 current/canonical docs를 정확히 안내
- v0.9 writer가 받을 입력 계약이 준비됨
```

---

### v0.9 Writer Foundation

목표:

```text
Summary / Analysis / Research writer의 최소 기반 구현
```

범위:

```text
- Summary writer V1
- Evidence Pack 기반 answer draft
- TurnContext / PromptPackage 입력 사용
- llm_profile 기반 writer/reasoner 선택
- unsupported/future-route 유지
- claim validation 최소형
```

금지:

```text
- full research loop
- multi-agent loop
- streaming frontend
- workspace memory
- vector search
- motif graph
```

---

### v0.10 Tool Engine / Execution Plan

목표:

```text
LLM 자유 tool-use 전에 deterministic tool abstraction을 먼저 만든다.
```

산출물:

```text
tool_engine/
├─ tool_registry.py
├─ tool_contract.py
├─ search_tools.py
├─ source_reader_tools.py
├─ evidence_tools.py
└─ execution_plan_runner.py
```

---

### v0.11 Research Planner / Evidence Judge

목표:

```text
research mode를 위한 planner와 evidence judge를 만든다.
```

산출물:

```text
research/
├─ research_plan.py
├─ research_planner.py
├─ search_task_runner.py
├─ evidence_judge.py
├─ counter_evidence_finder.py
├─ gap_analyzer.py
└─ stop_controller.py
```

---

### v0.12 Agentic Research Loop V1

목표:

```text
반복형 연구 루프 구현
```

구조:

```text
Plan
→ Search
→ Read
→ Judge
→ GapAnalyze
→ StopDecision
→ Repeat or Synthesize
```

---

### v0.13 Streaming / Visible Thinking

목표:

```text
사용자용 진행 상태와 streaming event contract 구현
```

산출물:

```text
streaming/
├─ stream_event.py
├─ stream_bus.py
├─ phase_mapper.py
└─ visible_thought.py

ui_events/
├─ status_message.py
├─ answer_stream_state.py
└─ frontend_event_contract.py
```

---

## 10. 최종 PM 판단

이 설계는 타당하다.
다만 지금 즉시 구현할 설계와 나중에 구현할 설계를 분리해야 한다.

### 지금 바로 할 것

```text
1. D 완료
2. 문서 정리
3. v0.8.5 설계 반영
4. v0.8.6 minimal runtime/context foundation
5. Final v0.8.x audit
```

### v0.9에서 할 것

```text
- writer foundation
- TurnContext / PromptPackage 기반 답변
- Evidence Pack 기반 summary/analysis 초안
```

### v0.10 이후로 미룰 것

```text
- full tool engine
- research planner
- evidence judge
- agentic loop
- streaming / visible thinking
- frontend UI event integration
```

최종 결론:

```text
Claude Code식 agentic loop를 지금 통째로 가져오지 않는다.
대신 현재 프로젝트의 DB/Search/Evidence 기반 위에
SemanticState → TurnContext → Runtime Profile → Writer → Tool Engine → Research Loop 순서로
점진적으로 얹는다.
```
