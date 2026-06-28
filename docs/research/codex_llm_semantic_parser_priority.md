# Codex 전달 문서: 질문 의미 파악용 LLM Semantic Parser 우선 도입

작성일: 2026-06-28

## 1. 이 문서의 목적

이 문서는 Codex가 현재 원신 스토리 연구 AI 프로젝트에서 다음 개발 방향을 명확히 이해하고 구현할 수 있도록 작성한 작업 지시 문서다.

핵심은 다음이다.

```text
사용자 질문을 먼저 LLM에 보내 의미를 파악하고,
그 결과를 기반으로 route / intent / entity / answer style / context reference를 결정한다.
```

현재 시스템은 로컬 LLM이 켜져 있어도, 질문 의미 파악은 대부분 규칙 기반 라우터가 담당한다. 그 결과 기본적인 정형 질문은 처리되지만, 자연스러운 대화형 질문에서는 한계가 드러난다.

예시:

```text
질문: 푸리나
→ basic_lookup / character_basic_info
→ 정상

질문: 푸리나의 기본 정보를 알려줘
→ basic_lookup / character_basic_info
→ 정상

질문: 푸리나에 대해서 요약해줘
→ summary / unsupported
→ 사용자가 기대한 의미와 다름
```

사람 입장에서 `푸리나에 대해서 요약해줘`는 대개 다음 의미다.

```text
푸리나의 기본 정보를 자연스럽게 요약해줘.
```

하지만 현재 라우터는 `요약`이라는 단어를 강하게 보고 summary route로 보내며, summary route가 아직 구현되지 않았기 때문에 unsupported가 된다.

따라서 다음 단계의 핵심은 검색 알고리즘 추가가 아니라, **사용자 질문 의미를 LLM으로 먼저 해석하는 구조**를 도입하는 것이다.

---

## 2. 현재 문제 요약

### 2.1 LLM이 켜져 있어도 질문 이해에는 거의 쓰이지 않음

현재 로컬 LLM은 주로 facts 기반 답변 앞의 짧은 문장 보정 또는 rewriter 역할로 사용된다.

즉, 실제 흐름은 다음에 가깝다.

```text
사용자 질문
→ deterministic router
→ route 결정
→ facts 조회
→ template answer
→ 일부 케이스에서 LLM rewriter
```

이 구조에서는 LLM이 켜져 있어도 사용자는 ChatGPT 같은 자연어 이해를 체감하기 어렵다.

---

### 2.2 규칙 기반 라우팅은 자연어 표현에 약함

사용자는 실제로 다음처럼 말한다.

```text
푸리나 알려줘
푸리나 요약해줘
푸리나에 대해서 간단히
스토리도 알려줘
좀 더 자세히
그럼 포칼로스랑 관계는?
근거는?
```

이런 표현은 단어 규칙만으로 안정적으로 처리하기 어렵다.

특히 다음을 구분해야 한다.

```text
푸리나 요약해줘
→ 캐릭터 기본정보를 짧게 요약

푸리나 스토리 요약해줘
→ 캐릭터 스토리/퀘스트 기반 summary

푸리나와 포칼로스 관계 알려줘
→ analysis

푸리나가 천리랑 관련 있다는 근거 찾아줘
→ research 또는 analysis

근거는?
→ 직전 답변에 대한 source/evidence 요청
```

이 구분은 단순 키워드 라우터보다 LLM semantic parser가 훨씬 적합하다.

---

### 2.3 답변 스타일도 질문 의미에서 파생되어야 함

현재는 `알려줘`에 대해 너무 많은 원문 필드가 그대로 출력되는 경향이 있다.

예를 들어 `안회광 알려줘`에 대해 R1부터 R5까지 전부 펼치면 정확할 수는 있지만, 기본 대화형 응답으로는 과하다.

기본적으로는 다음처럼 답해야 한다.

```text
안개를 가르는 회광은 5성 한손검이고, 보조 속성은 치명타 피해야.

핵심 효과는 원소 피해 보너스와 「무절의 문장」 스택을 통해 자신의 원소 피해를 올리는 구조야.

제련별 수치는 길어서, 원하면 R1~R5 전체 수치를 따로 보여줄게.
```

그리고 사용자가 다음처럼 명시할 때만 detail/raw 모드로 들어간다.

```text
R1부터 R5까지 보여줘
원문 그대로 보여줘
자세히 알려줘
```

즉 LLM semantic parser는 route만 정하는 것이 아니라, `requested_style`도 결정해야 한다.

---

## 3. 목표 구조

목표 흐름은 다음이다.

```text
사용자 질문
→ command guard
→ ConversationState 로드
→ LLM Semantic Parser
→ AnswerPlan JSON 생성
→ context resolver
→ deterministic resolver
→ DB facts/search/source reader/evidence pack 조회
→ grounded writer 또는 template writer
→ validator
→ 최종 답변
→ ConversationState 업데이트
```

중요한 점은 다음이다.

```text
LLM은 질문의 의미를 파악한다.
LLM은 답변 스타일을 정한다.
LLM은 후속 질문에서 생략된 대상을 복원한다.

하지만 LLM은 사실을 직접 만들어내면 안 된다.
사실은 DB/facts/evidence에서 온다.
```

---

## 4. 구현 핵심: LLM Semantic Parser

### 4.1 역할

LLM Semantic Parser의 역할은 답변 생성이 아니다.

역할은 사용자 질문과 최근 대화 컨텍스트를 받아서 실행 가능한 `AnswerPlan` JSON을 생성하는 것이다.

입력:

```json
{
  "user_query": "푸리나에 대해서 요약해줘",
  "conversation_state": {
    "active_entity": null,
    "active_topic": null,
    "last_route": null,
    "last_intent": null
  },
  "supported_routes": [
    "chitchat",
    "basic_lookup",
    "summary",
    "analysis",
    "research",
    "source_reader",
    "unsupported"
  ],
  "supported_basic_lookup_types": [
    "character",
    "weapon",
    "reliquary"
  ]
}
```

출력:

```json
{
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "entities": [
    {
      "name": "푸리나",
      "type": "character",
      "confidence": 0.92
    }
  ],
  "requested_style": "brief_summary",
  "detail_level": "low",
  "context_reference": null,
  "context_used": false,
  "needs_evidence": false,
  "needs_raw_source": false,
  "unsupported_reason": null
}
```

---

### 4.2 AnswerPlan 필드 제안

초기 schema는 다음 정도로 시작한다.

```json
{
  "route": "basic_lookup | summary | analysis | research | source_reader | chitchat | unsupported",
  "intent": "string",
  "entities": [
    {
      "name": "string",
      "type": "character | weapon | reliquary | book | quest | region | concept | unknown",
      "confidence": 0.0
    }
  ],
  "requested_style": "brief | default | detail | raw | evidence | analysis | research",
  "detail_level": "low | medium | high",
  "context_reference": "last_entity | last_topic | last_answer | null",
  "context_used": false,
  "needs_evidence": false,
  "needs_raw_source": false,
  "unsupported_reason": null
}
```

필수 원칙:

```text
1. LLM은 JSON만 출력한다.
2. JSON 파싱 실패 시 deterministic router로 fallback한다.
3. LLM이 추출한 entity는 반드시 DB resolver로 검증한다.
4. LLM output을 그대로 믿고 답변하면 안 된다.
```

---

## 5. 반드시 해결해야 하는 대표 케이스

### 5.1 기본정보 요약 케이스

```text
입력:
푸리나에 대해서 요약해줘

기대:
route=basic_lookup
intent=character_basic_info
entity=푸리나
requested_style=brief
```

현재처럼 `summary/unsupported`로 가면 실패다.

---

### 5.2 기본 무기 정보 케이스

```text
입력:
안회광 알려줘

기대:
route=basic_lookup
intent=weapon_basic_info
entity=안개를 가르는 회광
requested_style=default
```

여기서 기본 응답은 R1~R5 전체 dump가 아니라 핵심 요약이어야 한다.

---

### 5.3 명시적 세부 정보 요청

```text
입력:
안회광 R1부터 R5까지 보여줘

기대:
route=basic_lookup
intent=weapon_basic_info
entity=안개를 가르는 회광
requested_style=detail
detail_level=high
```

이때는 제련별 수치를 전부 보여줘도 된다.

---

### 5.4 후속 질문: 스토리도

이 케이스는 ConversationState와 함께 처리해야 한다.

```text
이전 질문:
푸리나 알려줘

현재 질문:
스토리도 알려줘

기대:
route=summary
intent=character_story_summary
entity=푸리나
context_reference=last_entity
context_used=true
```

summary route가 아직 완전 구현되지 않았다면, 현재 단계에서는 다음처럼 응답해도 된다.

```text
푸리나의 스토리 요청으로 이해했습니다.
아직 character_story_summary writer는 구현되지 않았습니다.
```

중요한 것은 `스토리도 알려줘`를 unsupported 단독 질문처럼 처리하지 않는 것이다.

---

### 5.5 후속 질문: 근거는?

```text
이전 질문:
푸리나 알려줘

현재 질문:
근거는?

기대:
route=source_reader 또는 basic_lookup evidence mode
intent=show_evidence
entity=푸리나
context_reference=last_answer
context_used=true
requested_style=evidence
```

---

### 5.6 분석 질문

```text
입력:
푸리나랑 포칼로스 관계는?

기대:
route=analysis
intent=character_relation_analysis
entities=[푸리나, 포칼로스]
requested_style=analysis
```

analysis writer가 아직 구현되지 않았다면 unsupported로 끝내더라도, route metadata는 analysis로 잡혀야 한다.

---

## 6. ConversationState의 최소 요구

Semantic parser는 ConversationState를 입력으로 받아야 한다.

최소 상태:

```json
{
  "active_entity": {
    "name": "푸리나",
    "type": "character",
    "canonical_id": "..."
  },
  "active_topic": "profile",
  "last_route": "basic_lookup",
  "last_intent": "character_basic_info",
  "last_answer_style": "default",
  "last_sources": [
    "project_amber:character:furina"
  ],
  "turn_count": 1
}
```

초기에는 메모리 DB가 필요 없다. 터미널 세션 내부 객체로만 유지해도 된다.

목표는 다음 후속 질문을 처리하는 것이다.

```text
스토리도 알려줘
더 자세히
짧게
근거는?
원문 보여줘
그럼 얘는?
```

---

## 7. Debug 출력 제안

현재 debug 출력은 다음과 비슷하다.

```text
[route=basic_lookup:0.88 | intent=character_basic_info | llm=used]
```

Semantic parser 도입 후에는 다음 정보를 표시하면 좋다.

```text
[route=basic_lookup | intent=character_basic_info | parser=llm | writer=llm | style=brief | context=no]
```

후속 질문이면:

```text
[route=summary | intent=character_story_summary | parser=llm | style=default | context=last_entity:푸리나]
```

이렇게 하면 현재 시스템이 질문을 어떻게 이해했는지 확인하기 쉽다.

---

## 8. 실패/폴백 정책

### 8.1 LLM parser 실패

다음 경우에는 기존 deterministic router로 fallback한다.

```text
1. Ollama connection error
2. timeout
3. invalid JSON
4. schema validation failure
5. route 값이 허용 enum 밖
```

fallback 결과에는 다음을 표시한다.

```text
parser=deterministic_fallback
```

---

### 8.2 entity 검증 실패

LLM이 entity를 추출했지만 DB에서 찾지 못하면 바로 답변하지 않는다.

대신 다음 중 하나를 수행한다.

```text
1. alias search로 후보를 찾는다.
2. 후보가 1개면 canonical entity로 보정한다.
3. 후보가 여러 개면 사용자에게 후보를 보여준다.
4. 후보가 없으면 unsupported로 처리한다.
```

예시:

```text
안회광
→ 안개를 가르는 회광
```

이 보정은 LLM에게 맡기기보다 alias/entity resolver가 담당해야 한다.

---

### 8.3 지원하지 않는 route

LLM parser가 summary/analysis/research를 잡았지만 해당 writer가 아직 구현되지 않았다면, 다음처럼 응답한다.

```text
질문 의도는 `character_story_summary`로 이해했습니다.
다만 현재 버전에서는 이 답변 writer가 아직 구현되지 않았습니다.
현재 지원되는 것은 캐릭터/무기/성유물 기본정보 조회입니다.
```

중요한 것은 route metadata를 잘못 basic_lookup으로 돌려서 처리하지 않는 것이다.

---

## 9. 테스트 케이스 제안

parser 평가셋에 최소 다음을 넣는다.

```json
[
  {
    "query": "푸리나",
    "expected_route": "basic_lookup",
    "expected_intent": "character_basic_info",
    "expected_entity": "푸리나",
    "expected_style": "default"
  },
  {
    "query": "푸리나에 대해서 요약해줘",
    "expected_route": "basic_lookup",
    "expected_intent": "character_basic_info",
    "expected_entity": "푸리나",
    "expected_style": "brief"
  },
  {
    "query": "푸리나 스토리 요약해줘",
    "expected_route": "summary",
    "expected_intent": "character_story_summary",
    "expected_entity": "푸리나"
  },
  {
    "query": "안회광 알려줘",
    "expected_route": "basic_lookup",
    "expected_intent": "weapon_basic_info",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "default"
  },
  {
    "query": "안회광 R1부터 R5까지 보여줘",
    "expected_route": "basic_lookup",
    "expected_intent": "weapon_basic_info",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "detail"
  },
  {
    "query": "나선비경 티어 알려줘",
    "expected_route": "unsupported",
    "expected_intent": "guide_or_meta_request"
  },
  {
    "query": "푸리나랑 포칼로스 관계는?",
    "expected_route": "analysis",
    "expected_intent": "character_relation_analysis"
  }
]
```

ConversationState 평가셋도 별도로 둔다.

```json
[
  {
    "history": [
      {
        "user": "푸리나 알려줘",
        "active_entity": "푸리나"
      }
    ],
    "query": "스토리도 알려줘",
    "expected_route": "summary",
    "expected_entity": "푸리나",
    "expected_context_used": true
  },
  {
    "history": [
      {
        "user": "안회광 알려줘",
        "active_entity": "안개를 가르는 회광"
      }
    ],
    "query": "R1부터 R5까지 보여줘",
    "expected_route": "basic_lookup",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "detail",
    "expected_context_used": true
  }
]
```

---

## 10. 구현 순서 제안

### Step 1. AnswerPlan schema 추가

파일 위치는 현재 구조에 맞게 정한다.

예상 후보:

```text
src/genshin_lore_db/search_engine/answer_plan.py
src/genshin_lore_db/search_engine/semantic_parser.py
```

---

### Step 2. Ollama 기반 parser 함수 추가

예상 함수:

```python
def parse_query_with_llm(
    query: str,
    conversation_state: ConversationState | None,
    *,
    model: str,
    timeout: float = 30.0,
) -> AnswerPlan:
    ...
```

주의:

```text
- 답변 생성 금지
- JSON only
- schema validation
- 실패 시 error result 반환
```

---

### Step 3. 기존 router 앞에 parser 삽입

기본 흐름:

```text
if llm_enabled:
    plan = parse_query_with_llm(...)
    if plan.ok:
        use plan
    else:
        fallback to deterministic router
else:
    deterministic router
```

---

### Step 4. deterministic resolver 연결

LLM이 만든 AnswerPlan을 그대로 실행하지 말고, 기존 alias/entity lookup과 연결해 검증한다.

```text
LLM entity: 안회광
resolver canonical: 안개를 가르는 회광
type: weapon
```

---

### Step 5. requested_style 반영

`basic_lookup` 답변에서 최소 다음을 분리한다.

```text
default:
- 핵심 요약 중심
- 긴 R1~R5 dump 생략 가능

detail:
- 전체 필드 출력
- R1~R5 포함

raw:
- 원문/DB 필드 중심
```

---

### Step 6. ConversationState v0.1 추가

터미널 chat loop에서 최소 세션 상태를 유지한다.

```text
active_entity
active_topic
last_route
last_intent
last_answer_style
last_sources
```

답변 후 상태를 업데이트한다.

---

## 11. 완료 기준

이 작업의 완료 기준은 다음이다.

```text
1. `푸리나에 대해서 요약해줘`가 summary/unsupported로 가지 않는다.
2. 해당 질문은 basic_lookup + character_basic_info + brief/default style로 처리된다.
3. `안회광 알려줘`는 weapon_basic_info로 처리하되, 기본 응답에서 R1~R5를 무조건 모두 dump하지 않는다.
4. `안회광 R1부터 R5까지 보여줘`는 detail style로 처리된다.
5. `스토리도 알려줘`는 직전 active_entity를 사용하려고 시도한다.
6. LLM parser 실패 시 기존 deterministic router로 fallback한다.
7. LLM parser가 만든 entity는 DB resolver로 검증된다.
8. debug 출력에서 parser, style, context 사용 여부가 보인다.
```

---

## 12. 가장 중요한 원칙

이 작업의 핵심은 LLM을 더 자유롭게 풀어주는 것이 아니다.

핵심은 다음이다.

```text
LLM은 사용자 질문의 의미를 이해한다.
DB는 사실을 제공한다.
Writer는 DB facts 안에서 자연스럽게 말한다.
Validator는 LLM이 선을 넘지 못하게 한다.
```

따라서 Codex는 다음 방향으로 구현해야 한다.

```text
질문 의미 파악:
LLM 우선

사실 조회:
DB 우선

답변 생성:
facts/evidence 기반

검증:
deterministic validator 우선
```

이 구조가 들어가야 프로젝트가 단순 검색 CLI에서 벗어나, DB 기반 정확성과 ChatGPT식 자연어 UX를 동시에 가진 대화형 원신 스토리 연구 AI로 발전할 수 있다.
