# Current Status and Stage Decisions

## 1. 문서 목적

이 문서는 Genshin Impact Story AI의 현재 구현 상태를 점검하고, 다음 질문에 대한 판단을 정리한다.

```text
이 프로젝트는 이미 로컬 LLM이나 API나 도구를 쥐어주고 “AI가 알아서 해라” 구조가 완성된 상태인가?
아니면 아직 그 단계가 아닌가?
없는 기능들은 놓친 것인가, 아니면 의도적으로 뒤로 미룬 것인가?
```

결론은 다음과 같다.

```text
현재 프로젝트는 developer-facing retrieval core + local LLM rewriter MVP 단계다.

검색, 정형 QA, Evidence Pack, 로컬 LLM rewriter는 작동한다.
하지만 autonomous tool-calling agent, API server, planner, conversational orchestrator는 아직 완성된 상태가 아니다.

대부분의 큰 기능은 놓친 것이 아니라 아직 개발 단계가 아니어서 미룬 것이다.
다만 basic_lookup 내부의 validator 약점과 일부 출력 품질 문제는 지금 바로 고쳐야 하는 누락/버그에 가깝다.
```

---

## 2. 현재 작동하는 것

현재 프로젝트에서 작동 중인 핵심 기능은 다음과 같다.

```text
Project Amber 기반 데이터 수집/정규화
SQLite FTS 기반 검색
route CLI
search CLI
investigate CLI
answer CLI
basic_lookup 정형 QA
Evidence Pack 초안
LLM prompt package 생성
Ollama 기반 local LLM rewriter
간단한 validator
```

특히 로컬 LLM 호출은 실제로 작동한다.

예시 출력:

```json
"llm": {
  "enabled": true,
  "used": true,
  "model": "llama3.2:1b",
  "ok": true,
  "error": null
}
```

따라서 “로컬 LLM이 아예 안 돈다”는 상태는 아니다.

---

## 3. 현재 로컬 LLM의 실제 역할

현재 LLM은 자유로운 연구형 답변 생성기가 아니다.

현재 구조는 다음에 가깝다.

```text
공식 데이터에서 facts 추출
→ 템플릿 draft 생성
→ 로컬 LLM이 문장만 다듬음
→ validator 통과 시 final_answer로 사용
```

즉 현재 LLM은 다음 역할이다.

```text
rewriter
문장 다듬기
정형 답변 자연어화
```

아직 다음 역할은 아니다.

```text
planner
tool-calling agent
research analyst
multi-step investigator
autonomous answer writer
conversation orchestrator
```

현재 LLM 프롬프트는 facts와 draft에 있는 정보만 사용하도록 제한되어 있다. 이는 환각을 줄이기 위한 좋은 초기 안전장치다.

다만 이 구조에서는 LLM이 새로운 스토리 정보, 캐릭터 사용법, 별자리 효과, 연구 가설 등을 독립적으로 추가할 수 없다. 그 정보는 먼저 facts extractor, Source Reader, Evidence Pack, route별 writer에서 제공되어야 한다.

---

## 4. 아직 완성되지 않은 것

현재 프로젝트에는 아직 다음 기능이 완성되어 있지 않다.

```text
API server
tool-calling agent
LLM planner
Conversation Orchestrator
Query Frame 기반 질문 해석
Source Reader
Summary Index
summary route 실제 답변 생성
analysis route 실제 답변 생성
research route 실제 답변 생성
guide route
Multi-Scout research loop
vector search
motif index
graph search
translation diff index
counter-evidence search
웹 UI
source viewer
workspace memory
```

이것들은 “프로젝트가 망가져서 안 되는 기능”이 아니라, 대부분 아직 구현 단계가 오지 않은 상위 기능이다.

---

## 5. 왜 아직 tool-calling agent를 만들면 안 되는가

“로컬 LLM이나 API에게 도구를 쥐어주고 알아서 해라” 구조를 만들려면, 먼저 AI가 실제로 사용할 도구들이 충분히 준비되어야 한다.

필요한 도구 예시:

```text
source_reader
summary_index_search
raw_drill_down
evidence_pin_builder
counter_search
motif_search
graph_search
translation_diff_search
multi_scout_retriever
hypothesis_builder
route별 validator
```

하지만 현재는 대부분 아직 구현 전이다.

지금 바로 agent를 만들면 구조가 이렇게 된다.

```text
AI: 검색해볼게
도구: FTS 검색만 가능

AI: 원문 확인해볼게
도구: Source Reader 없음

AI: 반례 찾아볼게
도구: counter search 없음

AI: 연구해볼게
도구: summary/motif/graph 없음
```

이 경우 AI는 도구를 쓰는 것처럼 보이지만, 실제로는 검색 결과 몇 개를 보고 감으로 답하게 된다. 이는 프로젝트 목표인 근거 기반 연구 AI와 맞지 않는다.

따라서 agent/API/conversation orchestrator는 나중 단계로 미루는 것이 맞다.

---

## 6. 놓친 것이 아니라 아직 단계가 아닌 것

다음 기능들은 현재 없더라도 이상하지 않다.

```text
API server
tool-calling agent
LLM planner
Conversation Orchestrator
summary/analysis/research 실제 writer
Multi-Scout research loop
vector/motif/graph search
웹 UI
source viewer
workspace memory
```

이 기능들은 다음 순서로 하부 구조가 갖춰진 뒤 구현해야 한다.

```text
basic_lookup 안정화
→ Source Reader
→ Summary Index
→ summary route
→ analysis route
→ research route
→ Multi-Scout
→ API/tool-calling agent
→ Conversation Orchestrator
→ Web UI
```

따라서 이들은 “놓친 기능”이라기보다 “아직 개발 단계가 아닌 기능”이다.

---

## 7. 놓친 것에 가까운 부분

반면 현재 단계에서도 바로 잡아야 하는 문제들이 있다.

### 7.1 LLM output required-field validation 부족

현재 LLM이 draft에 있던 정보를 final_answer에서 삭제해도 validator가 통과할 수 있다.

예시:

```text
draft_answer:
- 돌파 보너스: 치명타 확률

final_answer:
돌파 보너스 항목 누락

validation:
ok: true
```

이것은 현재 basic_lookup 단계에서도 잡아야 하는 문제다.

해결 방향:

```text
intent별 required field 정의
LLM output이 필수 필드를 누락했는지 검사
누락 시 LLM 답변 폐기
draft_answer로 fallback
validator reason에 missing_required_field 기록
```

예시 required fields:

```text
character_basic_info:
- name
- element
- weapon_type
- region
- birthday
- constellation
- special_prop

weapon_basic_info:
- name
- rank
- weapon_type
- special_prop
- refinement information

reliquary_effect_lookup:
- name
- set effects
```

---

### 7.2 무기 제련 효과 출력 문제

현재 무기 답변에서 제련 효과가 “1재련 효과”처럼 출력될 수 있다.

이는 데이터적으로는 1재련 기준 설명일 수 있지만, 사용자 입장에서는 무기 효과가 1재련에 고정된 것처럼 보일 수 있다.

수정 방향:

```text
효과 수치는 제련 단계에 따라 증가합니다.
- 1재련: ...
- 2재련: ...
- 3재련: ...
- 4재련: ...
- 5재련: ...
```

또는 compact 모드에서는 다음처럼 표현한다.

```text
1재련 기준 효과: ...
효과 수치는 제련 단계에 따라 증가합니다.
```

---

### 7.3 캐릭터 facts 부족

현재 character_basic_info는 기본 프로필 중심이다.

현재 포함되는 정보:

```text
이름
등급
원소
무기
지역
생일
칭호
소개
운명의 자리 이름
CV
돌파 보너스
출처
```

추가가 필요한 정보:

```text
별자리 C1~C6 효과
전투 특성
패시브 특성
캐릭터 스토리 연결
음성/대사 연결
관련 임무/문서 연결
```

다만 모든 정보를 기본정보 답변에 항상 출력하면 안 된다. facts는 넓게 만들고, route/intent별로 필요한 정보만 출력해야 한다.

---

### 7.4 문서와 실제 구현 상태의 정합성

README나 docs가 “연구형 AI 에이전트”처럼 보이는데 실제 구현이 아직 검색 코어 + rewriter 단계라면 혼동될 수 있다.

문서에는 다음을 명시해야 한다.

```text
현재는 autonomous agent가 아니라 developer-facing retrieval core이다.
tool-calling agent와 conversational orchestrator는 summary/source reader/research scout 이후 단계다.
현재 LLM은 answer writer가 아니라 rewriter다.
```

---

## 8. 현재 단계의 정확한 이름

현재 프로젝트 상태를 가장 정확히 표현하면 다음과 같다.

```text
Developer-facing Retrieval Core MVP
+ Basic Lookup QA
+ Local LLM Rewriter
+ Evidence Pack Prototype
```

아직 다음 단계는 아니다.

```text
Autonomous Research Agent
Conversational ChatGPT-like Assistant
Full Tool-calling LLM System
API-backed AI Service
```

즉 현재 프로젝트는 최종 AI 서비스의 실패한 버전이 아니라, 그 서비스를 만들기 위한 하부 코어를 구축 중인 상태다.

---

## 9. 단계별 개발 계획

### v0.6.x — basic_lookup 안정화

목표:

```text
정형 QA가 틀리지 않게 만들기
```

작업:

```text
LLM output required-field validation 추가
무기 제련 R1~R5 출력 수정
캐릭터 별자리 facts 추가
캐릭터 특성 facts 추가
template fallback 안정화
basic_lookup 평가셋 확대
```

---

### v0.7 — Source Reader + Summary Index

목표:

```text
요약 라우트와 원문 확인 구조의 기반 마련
```

작업:

```text
Source Reader 구현
document_summaries 생성
segment_summaries 생성
summary index 구축
summary → raw source 연결
Evidence Pin 생성
```

---

### v0.8 — summary / analysis route

목표:

```text
단순 검색이 아니라 원문 기반 요약과 분석 가능
```

작업:

```text
summary route 실제 답변 생성
analysis route 실제 답변 생성
공식 사실/해석 분리
route별 validator 강화
```

---

### v0.9 — research route + Multi-Scout

목표:

```text
원신 세계관 구조를 탐색하고 가설과 반례를 정리
```

작업:

```text
research planner
summary scout
raw keyword scout
semantic scout
motif scout
graph scout
translation diff scout
counter-evidence scout
external frame scout
candidate merge/ranking
hypothesis builder
research validator
```

---

### v1.0 — API / Tool-calling Agent / Conversation Orchestrator

목표:

```text
ChatGPT처럼 자연스럽게 대화하면서 도구를 사용하고 근거 기반으로 답변
```

작업:

```text
API server
tool schema
LLM planner
Conversation Orchestrator
Query Frame
multi-turn context
source viewer
web UI
workspace memory
```

---

## 10. 현재 구현 상태 체크리스트

| 항목 | 현재 상태 | 판단 |
|---|---|---|
| Project Amber DB | 구현됨 | 정상 |
| SQLite FTS search | 구현됨 | 정상 |
| route CLI | 구현됨 | 초안 |
| search CLI | 구현됨 | 정상 |
| investigate CLI | 구현됨 | Evidence Pack prototype |
| answer CLI | 구현됨 | basic_lookup 중심 |
| Ollama local LLM | 작동 확인 | rewriter 역할 |
| validator | 구현됨 | 약함, 강화 필요 |
| API server | 없음 | 아직 단계 아님 |
| tool-calling agent | 없음 | 아직 단계 아님 |
| planner | 없음 | 아직 단계 아님 |
| Source Reader | 없음 | 다음 단계 |
| Summary Index | 없음 | 다음 단계 |
| summary route writer | 없음 | 다음 단계 |
| analysis route writer | 없음 | 다음 단계 |
| research route | 구조만 있음 | 구현 전 |
| Multi-Scout | 없음 | research 단계 |
| vector search | 없음 | 후속 단계 |
| motif/graph search | 없음 | 후속 단계 |
| web UI | 없음 | 후순위 |

---

## 11. 개발 판단 기준

앞으로 기능을 볼 때 다음 기준으로 판단한다.

### 11.1 지금 고쳐야 하는 것

현재 구현된 기능의 정확도와 안전성에 직접 영향을 주는 것.

```text
validator 누락
facts extractor 누락
basic_lookup 출력 오류
LLM fallback 문제
테스트 부족
```

### 11.2 다음 단계에서 해야 하는 것

하부 기능이 생겨야 제대로 구현 가능한 것.

```text
Source Reader
Summary Index
Summary route
Analysis route
Research route
Multi-Scout
```

### 11.3 나중에 해야 하는 것

상위 UX와 서비스화 영역.

```text
API server
tool-calling agent
Conversation Orchestrator
웹 UI
워크스페이스 메모리
```

---

## 12. 최종 결론

이번 점검의 결론은 다음과 같다.

```text
큰 아키텍처 기능이 없는 것은 대부분 놓친 것이 아니다.
아직 개발 단계가 아니라서 의도적으로 미뤄둔 것이 맞다.

하지만 현재 이미 구현된 basic_lookup 안에서
LLM 출력 검증이 약한 문제,
무기 제련 표현 문제,
캐릭터 facts 부족 문제는 지금 고쳐야 하는 누락/품질 문제다.
```

따라서 지금 우선순위는 다음이다.

```text
1. basic_lookup validator 강화
2. 무기 제련 출력 수정
3. 캐릭터 facts 확장
4. 테스트 추가
5. Source Reader 구현
6. Summary Index 구현
7. summary/analysis/research 라우트로 확장
8. 그 다음 API/tool-calling/conversation layer 구현
```

가장 중요한 판단:

```text
현재 프로젝트는 “AI에게 도구 쥐어주고 알아서 하게 하는 완성형 에이전트”가 아니다.

현재 프로젝트는 그 에이전트를 만들기 위한 검색 코어, 정형 QA, Evidence Pack, LLM rewriter 기반 MVP다.
```

이 상태를 명확히 인식해야 이후 개발 순서가 꼬이지 않는다.
