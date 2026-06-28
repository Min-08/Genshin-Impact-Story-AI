# ChatGPT형 능동 연구 AI 최종 비전 문서

작성일: 2026-06-28

## 1. 문서 목적

이 문서는 원신 스토리 연구 AI 프로젝트의 최종 비전을 설명한다.

현재 프로젝트는 라우터, 알고리즘 기반 검색엔진, Project Amber DB, basic lookup, Source Reader, Evidence Pack, validator를 중심으로 한 **정확성 우선 MVP**를 만들고 있다.

하지만 최종 목표는 단순한 검색기나 정형 QA 프로그램이 아니다.

최종 목표는 다음과 같다.

```text
라우터와 알고리즘 기반 검색엔진으로 정확한 MVP를 먼저 만들고,
그 위에 QueryFrame, Tool Executor, Evidence Pack, ClaimGraph, Validator를 얹어서,
최종적으로 ChatGPT처럼 자유롭게 대화하고 능동적으로 연구하지만
공식 DB와 근거 통제를 잃지 않는 원신 스토리 연구 AI를 만든다.
```

더 짧게 말하면 다음과 같다.

```text
검색엔진을 만드는 것이 아니라,
검색엔진을 도구로 쓰는 ChatGPT형 연구 AI를 만드는 것이다.
```

---

## 2. 핵심 비전

이 프로젝트의 최종 비전은 다음 한 문장으로 정리할 수 있다.

```text
ChatGPT처럼 자유롭게 대화하지만,
공식 DB, 검색엔진, Evidence Pack, Validator가 사실성과 근거를 통제하는
능동형 원신 스토리 연구 AI.
```

여기서 중요한 것은 두 가지다.

첫째, **ChatGPT처럼 자유로워야 한다.**

사용자는 명령어처럼 질문하지 않아도 된다.

```text
푸리나 알려줘
스토리도
포칼로스랑 관계는?
근거는?
그럼 천리랑 연결될 가능성은?
반례도 찾아봐
```

AI는 이런 흐름을 자연스럽게 이해하고, 이전 대화의 맥락을 이어받아야 한다.

둘째, **ChatGPT처럼 자유롭지만 아무 말이나 하면 안 된다.**

공식 사실, 해석, 추측, 창의적 가설은 반드시 구분되어야 한다.

```text
공식 사실:
DB와 공식 원문으로 확인되는 내용

해석:
근거를 바탕으로 설명 가능한 의미

추측:
불확실하지만 검토할 수 있는 가능성

창의적 가설:
흥미롭지만 근거 수준을 낮게 표시해야 하는 가설
```

이 경계를 유지하는 것이 이 프로젝트의 핵심이다.

---

## 3. 현재 MVP의 의미

현재 MVP는 겉보기에는 프로그램적인 구조다.

```text
사용자 질문
→ 라우터
→ basic_lookup / summary / analysis / research 분기
→ DB 검색
→ facts 추출
→ 템플릿 답변
→ LLM rewriter
→ validator
```

이 구조는 ChatGPT처럼 보이지 않을 수 있다.  
답변이 정형화되어 있고, LLM의 자유도도 낮다.

하지만 이 MVP는 버릴 구조가 아니다.

이 MVP는 최종 대화형 연구 AI의 **하부 엔진**이다.

```text
basic_lookup
search_text
resolve_entities
read_window
read_parallel
pin_evidence
build_evidence_pack
validate_answer
```

이런 기능들이 안정적으로 존재해야, 나중에 LLM이 자유롭게 움직여도 근거 없는 답변으로 무너지지 않는다.

따라서 현재 MVP는 최종 목표의 실패한 버전이 아니다.  
최종 목표를 가능하게 만드는 기반이다.

---

## 4. 현재 MVP와 최종 AI의 관계

현재 구조:

```text
사용자 질문
→ 라우터
→ DB 조회
→ 템플릿 답변
→ 제한적 LLM rewriter
→ validator
```

최종 구조:

```text
사용자 질문
→ Conversation Orchestrator
→ LLM QueryFrame Parser
→ Entity Resolver
→ Route Decision
→ LLM Planner
→ Tool Executor
→ Search Engine / Source Reader / Evidence Pack
→ ClaimGraph
→ Grounded LLM Writer
→ Validator
→ ChatGPT식 자연어 답변
```

즉 최종 리팩토링은 현재 구조를 폐기하는 것이 아니다.

```text
현재 DB 기반 엔진 위에
ChatGPT식 대화 이해와 능동 연구 레이어를 얹는 것이다.
```

이것이 이 프로젝트의 가장 중요한 방향이다.

---

## 5. 최종 사용자 경험

최종 사용자는 검색어를 잘 넣는 사람이 아니어도 된다.  
그냥 ChatGPT에게 묻듯이 질문할 수 있어야 한다.

예시 대화:

```text
사용자:
푸리나 알려줘

AI:
푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야...
```

```text
사용자:
스토리도

AI 내부 해석:
이전 대상 = 푸리나
질문 의미 = 푸리나의 스토리 요약
route = summary
```

```text
사용자:
포칼로스랑 관계는?

AI 내부 해석:
대상 = 푸리나 + 포칼로스
route = analysis
필요 도구 = search_text, read_window, build_evidence_pack
```

```text
사용자:
그럼 천리랑 연결될 가능성은?

AI 내부 해석:
route = research
speculation_allowed = true
필요 작업 = 직접 근거, 간접 근거, 반례 후보, 가설 비교
```

```text
사용자:
반례도 찾아봐

AI 내부 해석:
직전 research 질문의 반례 후보 탐색
context_reference = last_research_question
tool = find_counter_evidence
```

이런 흐름이 자연스럽게 이어지는 것이 최종 사용자 경험이다.

---

## 6. 검색엔진이 아니라 검색엔진을 쓰는 AI

이 프로젝트의 핵심은 단순 검색 성능이 아니다.

검색엔진은 최종 AI가 사용할 도구다.

사용자가 직접 다음처럼 검색어를 잘 조합해야 한다면 아직 검색기다.

```text
파네스 천리 동일 존재 창조자 질서 왕좌
```

최종 AI는 사용자가 이렇게 말해도 된다.

```text
파네스랑 천리가 같은 존재일 가능성 있어?
```

AI는 내부적으로 다음을 스스로 판단해야 한다.

```text
파네스 직접 언급을 찾아야 한다.
천리 직접 언급을 찾아야 한다.
창조자, 질서, 왕좌, 세계, 하늘 같은 간접 개념도 찾아야 한다.
다국어 표현 차이를 봐야 한다.
반례 후보도 찾아야 한다.
가설을 여러 개로 나누어 비교해야 한다.
```

이것이 능동 연구 AI다.

---

## 7. 능동 연구 AI의 의미

능동 연구 AI는 단순히 사용자가 입력한 단어를 검색하지 않는다.

능동 연구 AI는 다음을 수행한다.

```text
질문을 분해한다.
관련 엔티티를 resolve한다.
사용자가 말하지 않은 관련 개념을 제안한다.
검색 질의를 여러 개 만든다.
직접 언급과 간접 근거를 나눈다.
원문 주변 문맥을 읽는다.
다국어 표현 차이를 확인한다.
반례 후보를 찾는다.
여러 가설을 세운다.
각 가설의 근거와 약점을 비교한다.
확정 가능한 것과 불확실한 것을 분리한다.
```

예시:

```text
질문:
파네스와 천리가 같은 존재일 가능성 조사해줘
```

능동 연구 AI가 해야 할 내부 작업:

```text
1. 파네스 직접 언급 검색
2. 천리 직접 언급 검색
3. 천리의 주관자, Heavenly Principles, Sustainer 등 별칭 확장
4. 창조자/왕좌/하늘/질서 관련 표현 검색
5. 관련 책/퀘스트/대사 주변 문맥 읽기
6. 한중일영 표현 차이 비교
7. 동일 존재설, 계승설, 같은 체계의 다른 존재설 등 가설 분리
8. 각 가설의 근거와 반례 정리
9. 현재 공식 근거로 확정할 수 없는 부분 표시
```

이것이 단순 검색기와 연구 AI의 차이다.

---

## 8. LLM 자유도의 점진적 확장

LLM의 자유도는 route에 따라 달라져야 한다.

```text
basic_lookup:
DB가 거의 모든 것을 결정한다.
LLM은 질문 이해와 표현만 담당한다.

summary:
LLM이 정해진 원문 범위 안에서 요약한다.

analysis:
LLM이 여러 근거를 묶어 해석한다.
공식 사실과 해석을 분리한다.

research:
LLM이 탐색 계획을 세우고, 도구를 선택하고, 가설과 반례를 비교한다.
다만 모든 주장은 Evidence Pack과 연결되어야 한다.
```

즉 자유도는 한 번에 열지 않는다.

```text
정형 조회
→ 원문 요약
→ 근거 기반 분석
→ 능동 연구
```

순서로 점진적으로 확장한다.

---

## 9. 자유도와 통제의 균형

이 프로젝트의 어려움은 자유도와 통제를 동시에 잡는 것이다.

자유도만 높이면 다음 문제가 생긴다.

```text
LLM이 그럴듯한 설정을 만들어낸다.
공식 사실과 추측이 섞인다.
출처 없는 관계를 단정한다.
사용자는 답변을 믿기 어려워진다.
```

통제만 강하면 다음 문제가 생긴다.

```text
답변이 검색 CLI처럼 딱딱하다.
사용자가 명령어처럼 질문해야 한다.
후속 질문을 이해하지 못한다.
AI가 사용자가 놓친 단서를 찾아주지 못한다.
```

따라서 목표는 다음 균형이다.

```text
표현은 자유롭게.
탐색은 능동적으로.
가설은 창의적으로.

하지만:
공식 사실은 DB 기반.
해석은 근거 기반.
추측은 추측으로 표시.
반례도 함께 표시.
출처는 Evidence Pack으로 고정.
```

---

## 10. Tool-Calling의 최종 의미

최종적으로 LLM은 도구를 사용할 수 있어야 한다.

하지만 도구 사용은 다음 방식이어야 한다.

```text
LLM이 ToolCall JSON을 제안한다.
프로그램이 ToolCall을 검사한다.
허용된 도구만 실행한다.
ToolResult를 LLM에게 돌려준다.
LLM은 결과를 보고 다음 도구 호출 또는 최종 답변을 결정한다.
```

즉 LLM이 직접 DB 파일을 열거나 SQL을 마음대로 실행하는 것이 아니다.

LLM은 다음처럼 말한다.

```json
{
  "type": "tool_call",
  "tool": "search_text",
  "reason": "파네스와 천리의 직접 언급을 찾기 위해 검색한다.",
  "input": {
    "query": "파네스 천리",
    "language": "ko",
    "limit": 10
  }
}
```

프로그램은 다음을 검사한다.

```text
이 route에서 search_text가 허용되는가?
limit가 예산 안에 있는가?
중복 검색이 아닌가?
입력이 정상인가?
```

통과하면 실행한다.

이 구조를 통해 LLM은 능동적으로 연구하지만, 프로그램은 실행과 안전을 통제한다.

---

## 11. Evidence Pack과 ClaimGraph

최종 답변은 단순 문장 묶음이 아니다.

analysis/research에서는 내부적으로 다음 구조가 필요하다.

```text
Evidence Pack:
검색과 원문 읽기로 고정된 근거 묶음

ClaimGraph:
각 주장과 그 주장을 지지하거나 반박하는 근거의 연결 구조
```

예시 claim:

```json
{
  "claim_id": "C1",
  "text": "파네스와 천리는 동일 존재일 가능성이 있다.",
  "claim_type": "hypothesis",
  "strength": "weak",
  "evidence_ids": ["E1", "E3"],
  "counter_evidence_ids": ["E7"],
  "source_level": "L0+inference",
  "certainty": 0.35
}
```

최종 답변은 자연스럽게 작성되어도 된다.  
하지만 내부적으로는 claim과 evidence가 연결되어 있어야 한다.

그래야 validator가 다음을 확인할 수 있다.

```text
이 주장은 근거가 있는가?
공식 사실인가, 해석인가, 추측인가?
반례가 있는데 무시하지 않았는가?
가설 강도와 표현 강도가 맞는가?
```

---

## 12. 최종 답변 스타일

최종 답변은 지금처럼 템플릿만 출력하는 형태가 아니다.

사용자 질문에 따라 자유롭게 구성되어야 한다.

예시:

```text
질문:
파네스와 천리가 같은 존재일 가능성 있어?
```

좋은 답변 구조:

```text
짧게 말하면, 가능성은 있지만 현재 공식 텍스트만으로 동일 존재라고 확정하기는 어렵다.

공식적으로 확인되는 것:
...

동일 존재설을 지지하는 근거:
...

다른 존재설을 지지하는 반례:
...

가능한 가설:
A. 동일 존재설 — 약함/중간
B. 같은 질서 체계의 다른 존재설 — 중간
C. 후대의 다른 체계라는 해석 — 약함

현재 결론:
...
```

이 답변은 ChatGPT처럼 읽히지만, 내부적으로는 Evidence Pack과 ClaimGraph에 묶여 있어야 한다.

---

## 13. 최종 아키텍처

최종 구조는 다음 계층으로 나눌 수 있다.

```text
Chat Layer
- terminal / API / web
- ConversationState 관리

Understanding Layer
- LLM QueryFrame Parser
- Rule Router
- Entity Resolver
- Route Merge Policy

Planning Layer
- BasicLookupPlan
- SummaryPlan
- AnalysisPlan
- ResearchPlan
- Tool Budget Policy

Tool Layer
- exact_lookup
- search_text
- read_unit
- read_window
- read_parallel
- pin_evidence
- build_evidence_pack
- find_counter_evidence

Evidence Layer
- EvidenceState
- EvidencePack
- ClaimGraph
- SourceLevel
- CounterEvidence

Writing Layer
- Template Writer
- Grounded LLM Writer
- Research Writer

Validation Layer
- Basic Fact Validator
- Summary Scope Validator
- Analysis Claim Validator
- Research Hypothesis Validator
```

이 구조에서 LLM은 여러 곳에 등장한다.

```text
QueryFrame Parser
Planner
Search query generator
Grounded Writer
Research Writer
```

하지만 모든 LLM 출력은 알고리즘 계층의 검증과 통제를 통과해야 한다.

---

## 14. 리팩토링 방향

최종 리팩토링은 단순히 코드를 예쁘게 나누는 작업이 아니다.

리팩토링의 목적은 다음이다.

```text
현재 프로그램 중심 MVP를
ChatGPT식 자유도 높은 대화형 연구 AI로 바꾸되,
정확성과 근거 통제를 잃지 않도록 계층을 재설계하는 것.
```

현재 MVP:

```text
검색엔진 + basic_lookup + rewriter
```

중간 단계:

```text
QueryFrame + ConversationState + Source Reader + grounded writer
```

최종 단계:

```text
Tool-Calling Research Agent + Evidence Pack + ClaimGraph + route별 validator
```

즉 리팩토링의 방향은 다음과 같다.

```text
기능을 제거하는 리팩토링이 아니라,
하부 엔진을 도구화하고,
LLM이 그 도구를 안전하게 사용할 수 있도록
대화형 오케스트레이션 레이어를 얹는 리팩토링.
```

---

## 15. 구현 순서의 비전

최종 비전을 위해 순서는 중요하다.

```text
1. basic_lookup 안정화
   - 캐릭터, 무기, 성유물, 별자리, 특성
   - facts extractor
   - validator
   - 평가셋

2. QueryFrame 도입
   - 질문 의미를 LLM이 구조화
   - 알고리즘이 검증

3. ConversationState 도입
   - 후속 질문 처리
   - active entity/topic 유지

4. Answer Style Controller
   - brief/default/detail/raw/evidence/analysis/research

5. Source Reader 연결
   - 원문 보기
   - 주변 문맥 읽기
   - 다국어 병렬 보기

6. summary route
   - 정해진 원문 범위 요약

7. analysis route
   - 관계/의미 해석
   - 공식 사실과 해석 분리

8. research route
   - 능동 검색
   - 도구 사용
   - 가설/반례 비교

9. Tool Executor
   - LLM ToolCall 제안
   - 프로그램 실행 통제

10. ClaimGraph / Research Memory
   - 가설 상태 관리
   - 근거와 반례 축적

11. API / Web UI
   - ChatGPT식 사용자 경험 제공
```

중요한 것은 UI를 너무 일찍 만들지 않는 것이다.  
먼저 AI가 사용할 수 있는 도구와 근거 체계를 만들어야 한다.

---

## 16. 이 프로젝트가 최종적으로 되어야 하는 것

이 프로젝트는 단순 백과사전이 아니다.

```text
원신 캐릭터 정보 조회기
원신 무기/성유물 DB 검색기
텍스트 검색 CLI
```

이것들이 전부가 아니다.

최종적으로는 다음에 가까워야 한다.

```text
공식 DB를 읽고,
원문을 파고들고,
여러 가설을 세우고,
반례를 찾고,
근거 강도를 비교하고,
사용자와 이어서 토론하는
능동 연구 에이전트.
```

즉 이 프로젝트는 검색엔진 자체가 목적이 아니다.

검색엔진은 AI의 눈과 손이다.  
Evidence Pack은 AI의 연구 노트다.  
Validator는 AI의 안전장치다.  
LLM은 사용자의 질문을 이해하고, 연구 방향을 잡고, 결과를 자연스럽게 설명하는 두뇌다.

---

## 17. 최종 정의

최종 프로젝트 정의:

```text
라우터와 알고리즘 기반 검색엔진으로 정확한 MVP를 먼저 구축하고,
이를 LLM이 사용할 수 있는 안전한 도구층으로 재구성한 뒤,
QueryFrame, ConversationState, Tool Executor, Evidence Pack, ClaimGraph, Validator를 결합해,
ChatGPT처럼 자유롭게 대화하고 능동적으로 연구하지만
공식 사실과 해석, 추측의 경계를 유지하는
DB 기반 원신 스토리 연구 AI.
```

더 짧은 정의:

```text
공식 DB와 검색엔진을 도구로 사용하는 ChatGPT형 능동 연구 AI.
```

가장 짧은 정의:

```text
근거에 묶인 자유로운 연구 AI.
```
