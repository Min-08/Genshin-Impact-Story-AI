# QueryFrame 기반 Tool-Calling Research AI 비전 문서

작성일: 2026-06-28

## 1. 문서 목적

이 문서는 원신 스토리 연구 AI가 단순 DB 검색기에서 벗어나, **질문을 자연어로 이해하고, 필요할 때 LLM이 도구 사용을 계획하며, 공식 근거 기반으로 분석과 연구를 수행하는 대화형 연구 AI**로 발전하기 위한 비전을 정리한다.

이 문서의 핵심 질문은 두 가지다.

```text
1. LLM이 이해한 사용자 질문을 알고리즘은 어떻게 안전하게 받아서 실행할 것인가?
2. analysis/research 라우트에서 LLM이 직접 도구를 사용하는 구조는 어떻게 설계할 것인가?
```

핵심 결론은 다음이다.

```text
LLM은 질문을 이해해서 구조화된 명령서로 바꾼다.
알고리즘은 그 명령서를 검증하고 실행한다.

analysis/research부터는 LLM이 도구 사용 계획을 세운다.
하지만 실제 도구 실행, 예산 제한, 출처 고정, 검증은 프로그램이 통제한다.
```

즉 이 프로젝트에서 LLM은 자유롭게 아무 말이나 하는 챗봇이 아니라, **질문 의미 해석기, 탐색 계획자, 근거 기반 writer**다.

프로그램은 **DB 조회기, 도구 실행기, 검증기, 안전장치**다.

---

## 2. 핵심 철학

이 프로젝트의 최종 목표는 다음 문장으로 요약할 수 있다.

```text
ChatGPT처럼 자연스럽게 질문을 이해하고 답하지만,
사실 판단은 DB와 Evidence Pack, Validator가 통제하는 연구 AI.
```

따라서 다음 원칙을 유지한다.

```text
질문 이해는 LLM에게 맡긴다.
사실 검증은 알고리즘에게 맡긴다.
도구 선택은 LLM에게 허용한다.
도구 실행은 프로그램이 통제한다.
최종 답변은 LLM이 쓰되, Evidence Pack과 Validator가 묶어둔다.
```

LLM을 쓰는 이유는 자연어 이해와 복잡한 탐색 계획 때문이다.  
LLM에게 모든 사실 판단을 넘기는 것이 아니다.

---

## 3. LLM과 알고리즘의 역할 분리

### 3.1 LLM이 잘하는 것

```text
자연어 의미 해석
애매한 질문 분해
검색 질의 후보 생성
후속 질문 맥락 이해
관련 가능성 있는 개념 제안
가설 생성
근거를 사람이 읽기 좋게 설명
```

### 3.2 알고리즘이 책임져야 하는 것

```text
엔티티 canonical resolve
도구 허용 여부 판단
검색 실행
원문 window 읽기
중복 제거
source level 부여
tool budget 제한
facts/evidence 구조화
claim-evidence 연결 검사
validator/fallback
```

### 3.3 LLM에게 맡기면 안 되는 것

```text
DB에 없는 사실을 공식 설정처럼 말하기
도구 실행 권한 자체
SQL/파일 접근 직접 권한
출처 없는 claim 확정
검증 없이 memory 저장
budget 제한 무시
```

즉 LLM은 “생각하고 제안하는 쪽”이고, 프로그램은 “검증하고 실행하는 쪽”이다.

---

## 4. 자연어 질문을 알고리즘으로 넘기는 방식

사용자 질문은 자연어다.

```text
푸리나에 대해서 요약해줘
```

LLM은 이 질문에 직접 답하지 않는다.  
먼저 내부 실행용 구조로 바꾼다.

```json
{
  "schema_version": "query_frame.v0.1",
  "raw_query": "푸리나에 대해서 요약해줘",
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "target": {
    "surface": "푸리나",
    "type_hint": "character"
  },
  "requested_style": "brief",
  "depth": "low",
  "needs_context": false,
  "needs_evidence": false,
  "speculation_allowed": false,
  "confidence": 0.88
}
```

이 중간 표현을 `QueryFrame`이라고 부른다.

QueryFrame은 사용자의 질문을 알고리즘이 실행 가능한 형태로 바꾼 것이다.  
LLM은 답을 만든 것이 아니라, **사용자의 말뜻을 구조화한 것**이다.

---

## 5. QueryFrame의 역할

QueryFrame은 단순 route 분류가 아니다.  
질문을 여러 축으로 나누어 이해하는 내부 표현이다.

```text
target:
무엇에 대해 묻는가?

goal / intent:
무엇을 하려는가?

route:
basic_lookup, summary, analysis, research 중 어디로 갈 것인가?

depth:
얼마나 깊게 탐색할 것인가?

requested_style:
brief, default, detail, raw, evidence, analysis, research 중 어떤 답변 형태인가?

source_policy:
공식 근거만 쓸 것인가, 외부 자료도 허용할 것인가?

speculation_allowed:
추측을 허용하는가?

context_reference:
이전 대화를 이어받는가?
```

예시:

```text
푸리나 알려줘
→ basic_lookup / character_basic_info / default

푸리나에 대해서 요약해줘
→ basic_lookup / character_basic_info / brief

푸리나 스토리 요약해줘
→ summary / character_story_summary / default

푸리나랑 포칼로스 관계는?
→ analysis / character_relation_analysis / analysis

파네스와 천리가 같은 존재일 가능성 조사해줘
→ research / identity_hypothesis_investigation / research
```

---

## 6. QueryFrame은 후보일 뿐이다

LLM이 만든 QueryFrame을 그대로 믿으면 안 된다.

예를 들어 LLM이 다음처럼 판단할 수 있다.

```json
{
  "target": {
    "surface": "안회광",
    "type_hint": "weapon"
  }
}
```

알고리즘은 이 판단을 검증해야 한다.

```text
1. DB alias에 "안회광"이 있는가?
2. canonical title은 무엇인가?
3. content_type이 weapon인가?
4. 현재 route에서 지원 가능한가?
5. 실행 가능한 intent인가?
```

검증 후에야 다음처럼 확정한다.

```json
{
  "schema_version": "resolved_query_frame.v0.1",
  "route": "basic_lookup",
  "intent": "weapon_basic_info",
  "targets": [
    {
      "surface": "안회광",
      "canonical_name": "안개를 가르는 회광",
      "canonical_id": "project_amber:weapon:11509",
      "content_type": "weapon",
      "item_id": "11509"
    }
  ],
  "requested_style": "default",
  "executable": true
}
```

즉 흐름은 다음이다.

```text
사용자 질문
→ LLM QueryFrame Parser
→ QueryFrame 후보
→ Entity Resolver
→ Route Policy
→ ResolvedQueryFrame 확정
→ ExecutionPlan 생성
→ 실행
```

---

## 7. 내부 데이터 계층

### 7.1 RawQuery

사용자 입력 그대로의 데이터다.

```json
{
  "text": "푸리나에 대해서 요약해줘",
  "language": "ko",
  "session_id": "terminal-session",
  "turn_id": 12
}
```

### 7.2 QueryFrame

LLM이 이해한 의미다.

```json
{
  "schema_version": "query_frame.v0.1",
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "targets": [
    {
      "surface": "푸리나",
      "type_hint": "character",
      "confidence": 0.92
    }
  ],
  "requested_style": "brief",
  "depth": "low",
  "source_policy": "official_only",
  "speculation_allowed": false,
  "context_reference": null,
  "needs_evidence": false,
  "needs_raw_source": false
}
```

### 7.3 ResolvedQueryFrame

알고리즘이 DB로 검증한 버전이다.

```json
{
  "schema_version": "resolved_query_frame.v0.1",
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "targets": [
    {
      "surface": "푸리나",
      "canonical_name": "푸리나",
      "canonical_id": "project_amber:avatar:10000089",
      "content_type": "avatar",
      "item_id": "10000089"
    }
  ],
  "requested_style": "brief",
  "executable": true
}
```

### 7.4 ExecutionPlan

실제로 어떤 도구를 어떤 순서로 실행할지 나타낸다.

```json
{
  "schema_version": "execution_plan.v0.1",
  "route": "basic_lookup",
  "steps": [
    {
      "tool": "exact_lookup",
      "input": {
        "canonical_id": "project_amber:avatar:10000089"
      }
    },
    {
      "tool": "build_facts",
      "input": {
        "intent": "character_basic_info"
      }
    },
    {
      "tool": "write_answer",
      "input": {
        "style": "brief"
      }
    }
  ]
}
```

---

## 8. 라우트별 LLM 권한

LLM의 권한은 route에 따라 달라져야 한다.

```text
basic_lookup:
LLM 권한 매우 낮음.
질문 이해와 말투 조정 정도만 허용.
사실 판단 금지.

summary:
LLM 권한 중간.
정해진 원문 범위 안에서 요약 가능.
범위 밖 지식 추가 금지.

analysis:
LLM 권한 높음.
여러 근거를 묶어 해석 가능.
공식 사실과 해석 분리 필수.

research:
LLM 권한 가장 높음.
탐색 계획, 가설 생성, 반례 찾기 가능.
단, 모든 주장은 evidence와 confidence를 가져야 함.
```

이 구조는 “질문이 어려워질수록 LLM 권한을 늘린다”는 원칙이다.

하지만 권한을 늘린다는 말은 LLM이 마음대로 사실을 생성해도 된다는 뜻이 아니다.  
LLM의 창의성은 **탐색 계획과 가설 생성**에 쓰고, 공식 사실은 DB와 Evidence Pack이 고정해야 한다.

---

## 9. LLM 권한의 종류

LLM 권한은 하나가 아니다. 여러 권한으로 나누어 관리해야 한다.

```text
Parse 권한:
질문 의미 해석

Plan 권한:
어떤 도구를 쓸지 제안

Search 권한:
검색 질의 생성

Read 권한:
어떤 원문 구간을 읽을지 선택

Hypothesis 권한:
가능한 가설 생성

Write 권한:
최종 답변 작성

Memory 권한:
연구 메모리에 저장
```

라우트별 권한 예시는 다음과 같다.

| Route | Parse | Plan | Search | Read | Hypothesis | Write | Memory |
|---|---|---|---|---|---|---|---|
| chitchat | 낮음 | 없음 | 없음 | 없음 | 없음 | 낮음 | 없음 |
| basic_lookup | 중간 | 없음 | 낮음 | 없음 | 없음 | 낮음 | 없음 |
| summary | 중간 | 낮음 | 중간 | 중간 | 없음 | 중간 | 없음 |
| analysis | 높음 | 중간 | 중간 | 높음 | 낮음 | 높음 | 선택 |
| research | 높음 | 높음 | 높음 | 높음 | 높음 | 높음 | 선택 |

이렇게 나누면 “LLM 권한 확대”를 안전하게 관리할 수 있다.

---

## 10. LLM이 도구를 사용하는 방식

analysis/research 라우트부터는 LLM이 직접 도구 사용 계획을 세울 수 있어야 한다.

하지만 중요한 점은 다음이다.

```text
LLM이 도구를 직접 실행하는 것이 아니다.
LLM은 ToolCall JSON을 생성한다.
프로그램이 ToolCall을 검증하고 실행한다.
```

나쁜 구조:

```text
LLM에게 파일, DB, SQL, Python 접근을 자유롭게 줌
→ 알아서 검색하고 읽고 판단하게 함
```

좋은 구조:

```text
LLM이 ToolCall JSON 생성
→ Tool Executor가 정책 검사
→ 허용된 도구만 실행
→ ToolResult를 LLM에게 반환
→ 반복
```

표준 루프는 다음과 같다.

```text
사용자 질문
→ QueryFrame
→ route=research
→ LLM Planner
→ ToolCall JSON 생성
→ Program Tool Executor
→ ToolResult 반환
→ LLM이 추가 ToolCall 또는 finalize 생성
→ Evidence Pack 생성
→ Answer Writer
→ Validator
```

---

## 11. ToolCall 형식

LLM은 자연어로 “검색해볼게요”라고 말하지 않는다.  
반드시 구조화된 ToolCall을 출력한다.

```json
{
  "type": "tool_call",
  "tool": "search_text",
  "reason": "푸리나와 포칼로스의 직접 언급 후보를 찾기 위해 검색한다.",
  "input": {
    "query": "푸리나 포칼로스",
    "language": "ko",
    "content_types": ["quest", "avatar", "book"],
    "limit": 10
  }
}
```

프로그램은 다음을 검사한다.

```text
이 route에서 search_text가 허용되는가?
limit가 예산 안에 있는가?
content_type이 허용되는가?
query가 비어 있지 않은가?
같은 query를 반복하지 않는가?
```

통과하면 실행하고 ToolResult를 반환한다.

```json
{
  "type": "tool_result",
  "tool": "search_text",
  "ok": true,
  "results": [
    {
      "unit_id": "textunit:...",
      "title": "폰타인 마신임무 ...",
      "content_type": "quest",
      "language": "ko",
      "snippet": "...",
      "score": 0.83
    }
  ]
}
```

그다음 LLM은 필요한 경우 원문 주변부를 읽는다.

```json
{
  "type": "tool_call",
  "tool": "read_window",
  "reason": "검색 결과의 앞뒤 문맥을 확인한다.",
  "input": {
    "unit_id": "textunit:...",
    "before": 5,
    "after": 8
  }
}
```

---

## 12. 도구 카탈로그

초기 도구는 작고 명확해야 한다.

```text
resolve_entities:
표면 문자열을 canonical entity로 변환

exact_lookup:
canonical id 기반 정형 데이터 조회

search_text:
FTS/trigram/entity alias 기반 검색

read_unit:
특정 text unit 읽기

read_window:
특정 unit 주변 문맥 읽기

read_section:
문서의 특정 section 읽기

read_parallel:
같은 unit의 한중일영 병렬 표현 읽기

pin_evidence:
답변에 쓸 근거를 고정

build_evidence_pack:
evidence들을 라우트별 묶음으로 구성

find_counter_evidence:
반례 후보 검색

summarize_evidence:
Evidence Pack 내부 요약
```

처음부터 너무 많은 도구를 만들 필요는 없다.  
중요한 것은 LLM이 직접 DB를 만지는 것이 아니라, 이 도구 카탈로그 안에서만 움직이게 하는 것이다.

---

## 13. route별 Tool Allowlist

도구는 route별로 허용 범위를 나누어야 한다.

```json
{
  "basic_lookup": [
    "resolve_entities",
    "exact_lookup",
    "build_facts"
  ],
  "summary": [
    "resolve_entities",
    "search_text",
    "read_section",
    "read_window",
    "build_evidence_pack"
  ],
  "analysis": [
    "resolve_entities",
    "search_text",
    "read_window",
    "read_parallel",
    "pin_evidence",
    "build_evidence_pack"
  ],
  "research": [
    "resolve_entities",
    "search_text",
    "read_window",
    "read_parallel",
    "find_counter_evidence",
    "search_motifs",
    "search_similar_passages",
    "build_evidence_pack",
    "pin_evidence"
  ]
}
```

Tool Executor는 LLM이 낸 ToolCall을 실행하기 전에 반드시 allowlist를 확인한다.

---

## 14. Tool Budget

LLM이 무한히 검색하거나 읽으면 안 된다.  
route별 예산을 둔다.

```json
{
  "analysis": {
    "max_tool_calls": 8,
    "max_searches": 3,
    "max_windows": 5,
    "max_units": 50
  },
  "research": {
    "max_tool_calls": 24,
    "max_searches": 10,
    "max_windows": 20,
    "max_units": 200
  }
}
```

Budget은 단순 성능 문제가 아니라 품질 문제다.  
무한 검색을 허용하면 LLM이 “조금만 더 찾아보자”를 반복하고, 답변의 초점이 흐려진다.

---

## 15. Evidence-first 원칙

analysis/research에서 LLM이 검색 결과 몇 개만 보고 감으로 답하면 안 된다.

나쁜 흐름:

```text
검색 결과 몇 개 확인
→ LLM이 감으로 답변
```

좋은 흐름:

```text
검색 결과
→ read_window
→ evidence pin
→ evidence pack
→ claim 생성
→ claim별 evidence 연결
→ 답변
```

최종 답변은 반드시 Evidence Pack 위에서 작성되어야 한다.

---

## 16. EvidenceState와 EvidencePack

도구 결과를 단순히 LLM 대화창에 계속 던지면 관리가 어렵다.  
프로그램 내부에 EvidenceState를 누적해야 한다.

```json
{
  "search_results": [],
  "read_windows": [],
  "parallel_units": [],
  "evidence_pins": [],
  "counter_candidates": [],
  "limitations": []
}
```

일정 단계가 끝나면 EvidencePack으로 고정한다.

```json
{
  "schema_version": "evidence_pack.v1",
  "query": "...",
  "route": "research",
  "sources": [],
  "evidence": [],
  "counter_evidence": [],
  "coverage": {},
  "limitations": []
}
```

EvidencePack은 LLM writer가 사용할 수 있는 공식 입력이다.  
Writer는 EvidencePack 밖의 내용을 공식 사실처럼 말하면 안 된다.

---

## 17. Claim 기반 답변 구조

analysis/research 답변은 내부적으로 claim 단위로 관리해야 한다.

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

최종 답변은 자연스럽게 써도 된다.  
하지만 내부적으로는 claim과 evidence가 연결되어 있어야 한다.

Validator는 다음을 검사한다.

```text
이 claim에 evidence가 있는가?
가설을 사실처럼 말하지 않았는가?
반례를 무시하지 않았는가?
source level이 표시되었는가?
확신도와 근거 강도가 맞는가?
```

---

## 18. analysis route 표준 패턴

analysis는 이미 어느 정도 대상이 정해진 상태에서 의미를 해석하는 라우트다.

예시:

```text
푸리나랑 포칼로스 관계는?
```

표준 흐름:

```text
1. resolve_entities
2. search_text direct mentions
3. read_window 상위 결과 3~5개
4. read_parallel 필요 시 한중일영 비교
5. build_evidence_pack
6. answer writer
7. validator
```

ExecutionPlan 예시:

```json
{
  "route": "analysis",
  "intent": "character_relation_analysis",
  "targets": ["푸리나", "포칼로스"],
  "steps": [
    {
      "tool": "resolve_entities",
      "input": {
        "terms": ["푸리나", "포칼로스"]
      }
    },
    {
      "tool": "search_text",
      "input": {
        "query": "푸리나 포칼로스",
        "language": "ko",
        "limit": 10
      }
    },
    {
      "tool": "read_window",
      "input_from": "top_search_results",
      "before": 5,
      "after": 8
    },
    {
      "tool": "build_evidence_pack",
      "input": {
        "mode": "analysis",
        "roles": ["supports", "context", "ambiguous"]
      }
    }
  ]
}
```

analysis 답변 구조:

```text
1. 짧은 결론
2. 공식 원문에서 확인되는 사실
3. 그 사실로부터 가능한 해석
4. 조심해야 할 부분
5. 출처/근거
```

---

## 19. research route 표준 패턴

research는 LLM 권한이 가장 크다.  
대신 가장 강하게 통제해야 한다.

예시:

```text
파네스와 천리가 같은 존재일 가능성 조사해줘
```

표준 흐름:

```text
1. 문제 분해
2. 엔티티 resolve
3. 직접 언급 검색
4. 간접 개념 검색
5. 다국어 표현 비교
6. 반례 후보 검색
7. 관련 모티프 검색
8. Evidence Pack 생성
9. 가설 생성
10. 가설별 근거/약점 비교
11. Validator
```

research planner는 먼저 다음과 같은 구조를 만든다.

```json
{
  "route": "research",
  "research_question": "파네스와 천리가 같은 존재일 가능성",
  "hypotheses": [
    {
      "id": "H1",
      "claim": "파네스와 천리는 같은 존재일 수 있다."
    },
    {
      "id": "H2",
      "claim": "파네스와 천리는 같은 질서 체계에 속하지만 다른 존재일 수 있다."
    },
    {
      "id": "H3",
      "claim": "둘의 직접 연결은 약하고, 상징적 유사성만 있을 수 있다."
    }
  ],
  "search_plan": [
    {
      "goal": "파네스 직접 언급 수집",
      "tool": "search_text",
      "query": "파네스"
    },
    {
      "goal": "천리 직접 언급 수집",
      "tool": "search_text",
      "query": "천리"
    },
    {
      "goal": "동일성/계승/창조자/질서 관련 표현 수집",
      "tool": "search_text",
      "query": "천리 창조자 질서 세계"
    },
    {
      "goal": "반례 후보 수집",
      "tool": "find_counter_evidence",
      "query": "파네스 천리 다른 존재"
    }
  ]
}
```

---

## 20. research 답변 구조

research 답변은 하나의 결론을 단정하는 것이 아니라, 가능한 해석 공간을 보여줘야 한다.

권장 구조:

```text
1. 짧은 결론
2. 공식 텍스트에서 확인되는 사실
3. 가설 A/B/C
4. 각 가설의 근거
5. 각 가설의 약점
6. 반례 후보
7. 현재 확정 불가능한 부분
8. 추가로 읽어야 할 문서
```

가설 강도 라벨:

```text
강함:
직접 근거가 여러 개 있음

중간:
간접 근거가 있고 반례가 치명적이지 않음

약함:
모티프나 정황 근거 중심

상상적:
흥미롭지만 공식 근거는 부족함
```

---

## 21. Tool Executor의 역할

Tool Executor는 LLM과 실제 코드 사이의 안전한 중간 계층이다.

```text
LLM ToolCall JSON
→ schema validation
→ route allowlist check
→ budget check
→ duplicate call check
→ input normalization
→ actual tool execution
→ ToolResult JSON
```

Tool Executor가 없으면 LLM tool-calling은 위험하다.  
LLM은 도구를 “선택”할 수 있지만, 도구를 “실행”하는 권한은 프로그램에 있어야 한다.

---

## 22. Research Loop 의사코드

```python
def run_research_query(query, state):
    frame = parse_query_with_llm(query, state)
    resolved = resolve_frame(frame)

    plan = llm_make_research_plan(resolved, tool_catalog)

    evidence_state = EvidenceState()

    for i in range(max_tool_calls):
        tool_call = llm_next_tool_call(
            query=resolved,
            plan=plan,
            evidence_state=evidence_state,
            budget=remaining_budget()
        )

        if tool_call.type == "finalize":
            break

        checked = policy_check(tool_call, route="research")
        if not checked.ok:
            evidence_state.add_policy_rejection(checked)
            continue

        result = execute_tool(checked.tool_call)
        evidence_state.add_result(result)

    pack = build_evidence_pack(evidence_state)
    draft = llm_write_research_answer(query, pack)
    validation = validate_research_answer(draft, pack)

    if not validation.ok:
        draft = repair_or_fallback(draft, validation, pack)

    return final_answer
```

핵심은 `llm_next_tool_call()`이 직접 실행하지 않는다는 것이다.  
항상 `policy_check()`를 거쳐야 한다.

---

## 23. 전체 아키텍처 비전

최종 구조는 다음과 같다.

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

---

## 24. 단계별 적용 방향

### Step 1. QueryFrame 도입

현재 semantic parse를 확장해서 QueryFrame으로 만든다.

```text
route
intent
targets
requested_style
depth
source_policy
speculation_allowed
context_reference
```

### Step 2. Resolver로 QueryFrame 검증

LLM이 뽑은 target을 DB canonical id로 변환한다.

```text
푸리나 → project_amber:avatar:10000089
안회광 → project_amber:weapon:11509
```

### Step 3. Route별 ExecutionPlan 생성

basic_lookup은 프로그램이 거의 고정 계획으로 처리한다.  
analysis/research는 LLM planner가 계획을 생성한다.

### Step 4. Tool Executor 추가

LLM이 낸 ToolCall을 실제 함수 호출로 바꿔주는 계층을 만든다.

```text
ToolCall JSON
→ validate
→ execute
→ ToolResult JSON
```

### Step 5. EvidenceState / EvidencePack 누적

도구 결과를 그냥 LLM에게 던지지 말고, 내부 상태로 누적한다.

```text
search_results
read_windows
parallel_units
evidence_pins
counter_candidates
limitations
```

### Step 6. Claim-based Writer

research 답변은 claim 단위로 만든다.

```text
공식 사실
해석
가설
반례
불확실성
```

### Step 7. Route별 Validator

```text
basic_lookup:
필수 facts 보존

summary:
원문 범위 이탈 금지

analysis:
공식 사실/해석 분리

research:
가설/근거/반례/강도 표시
```

---

## 25. MVP와 최종 형태의 관계

현재 MVP는 단순 정보 응답을 프로그램이 직접 처리하는 구조다.

```text
basic_lookup
→ DB 조회
→ facts 생성
→ template draft
→ LLM rewriter
→ validator
```

이 구조는 버릴 것이 아니라, 최종 시스템의 안전한 하부 엔진으로 유지한다.

최종 구조는 이 엔진 위에 다음을 얹는 것이다.

```text
ConversationState
QueryFrame
Tool Executor
EvidenceState
ClaimGraph
Grounded Writer
Route별 Validator
```

즉 나중에 ChatGPT처럼 바꾼다는 것은 현재 구조를 폐기하는 것이 아니다.

```text
현재 DB 기반 엔진 위에
ChatGPT식 대화 이해와 도구 사용 레이어를 얹는 것이다.
```

---

## 26. 최종 정의

이 비전의 최종 형태는 다음과 같다.

```text
사용자가 자연어로 질문하면,
LLM이 질문을 QueryFrame으로 구조화하고,
알고리즘이 엔티티와 route를 검증하며,
analysis/research에서는 LLM이 ToolCall을 제안하고,
프로그램이 허용된 도구만 실행하고,
Evidence Pack과 ClaimGraph로 근거를 고정한 뒤,
LLM이 자연스럽게 답변하고,
Validator가 공식 사실·해석·추측의 경계를 검사하는
DB 기반 대화형 원신 스토리 연구 AI.
```

한 문장으로 줄이면 다음이다.

```text
LLM은 탐색과 해석을 주도하지만,
근거 고정과 실행 통제는 알고리즘이 담당하는
Grounded Tool-Calling Lore Research AI.
```
