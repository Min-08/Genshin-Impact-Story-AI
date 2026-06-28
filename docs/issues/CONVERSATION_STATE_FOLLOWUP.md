# Issue: ConversationState v0.1로 후속 질문 처리하기

작성일: 2026-06-28  
권장 위치: `docs/issues/CONVERSATION_STATE_FOLLOWUP.md`

## 1. 문제 요약

현재 터미널 QA 루프는 각 질문을 독립적으로 처리한다. 따라서 사용자가 이전 질문의 맥락을 생략한 후속 질문을 던지면 처리하기 어렵다.

예시:

```text
질문> 푸리나 알려줘
질문> 스토리도 알려줘
질문> 근거는?
질문> 더 자세히
```

사람은 두 번째 질문을 `푸리나의 스토리도 알려줘`로 이해한다. 세 번째 질문은 `방금 답변의 공식 근거를 보여줘`로 이해한다.

하지만 현재 구조에서는 각 질문이 독립 입력이므로, `스토리도 알려줘`, `근거는?`, `더 자세히`에 대상이 없다.

---

## 2. 목표

대화형 QA가 직전 대화의 중심 대상과 주제를 기억하도록 한다.

초기 목표는 장기 메모리가 아니다. 터미널 세션 안에서만 유지되는 짧은 ConversationState v0.1이면 충분하다.

v0.6.4 기준으로 이 세션 한정 v0.1은 구현됐다. 파일/DB 저장, 장기 사용자 메모리, API 서버 상태 관리는 이번 범위에 포함하지 않는다.

---

## 3. 최소 상태 구조

초기 ConversationState는 다음 정도로 시작한다.

```json
{
  "active_entity": {
    "name": "푸리나",
    "content_type": "avatar",
    "canonical_id": "project_amber:avatar:10000089",
    "item_id": "10000089"
  },
  "active_topic": "profile",
  "last_route": "basic_lookup",
  "last_intent": "character_basic_info",
  "last_answer_style": "default",
  "last_sources": [
    {
      "source": "project_amber",
      "language": "ko"
    }
  ],
  "turn_count": 1
}
```

---

## 4. 처리해야 하는 후속 질문

### 4.1 스토리도 알려줘

이전 상태:

```json
{
  "active_entity": {
    "name": "푸리나",
    "content_type": "avatar"
  },
  "active_topic": "profile"
}
```

입력:

```text
스토리도 알려줘
```

기대 해석:

```json
{
  "resolved_query": "푸리나의 스토리를 알려줘",
  "route": "summary",
  "intent": "character_story_summary",
  "context_reference": "last_entity",
  "context_used": true
}
```

### 4.2 근거는?

입력:

```text
근거는?
```

기대 해석:

```json
{
  "resolved_query": "방금 답변의 공식 근거를 보여줘",
  "route": "source_reader",
  "intent": "show_evidence",
  "context_reference": "last_answer",
  "context_used": true,
  "requested_style": "evidence"
}
```

### 4.3 더 자세히

입력:

```text
더 자세히
```

기대 해석:

```json
{
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "context_reference": "last_entity",
  "context_used": true,
  "requested_style": "detail"
}
```

### 4.4 R1부터 R5까지 보여줘

이전 질문이 `안회광 알려줘`였을 경우:

```json
{
  "route": "basic_lookup",
  "intent": "weapon_basic_info",
  "entity": "안개를 가르는 회광",
  "context_reference": "last_entity",
  "context_used": true,
  "requested_style": "detail"
}
```

---

## 5. 구현 제안

### 5.1 `ConversationState` 모델 추가

권장 위치:

```text
src/genshin_lore_db/search_engine/conversation.py
```

예상 클래스:

```python
@dataclass
class ConversationState:
    active_entity: dict[str, Any] | None = None
    active_topic: str | None = None
    last_route: str | None = None
    last_intent: str | None = None
    last_answer_style: str | None = None
    last_sources: list[dict[str, Any]] = field(default_factory=list)
    turn_count: int = 0
```

### 5.2 terminal loop에서 상태 유지

현재 터미널 루프는 질문마다 독립 실행된다. 루프 시작 전에 상태 객체를 만들고, 매 답변 후 업데이트한다.

```text
state = ConversationState()

while True:
    query = input(...)
    result = answer_question(..., conversation_state=state)
    state.update_from_result(result)
```

### 5.3 semantic parser 입력에 state 포함

LLM parser prompt에 최근 상태를 제공하는 것은 후속 과제다. v0.6.4에서는 deterministic context resolver가 먼저 후속 질문을 복원하고, 그 결과를 route metadata에 남긴다.

```json
{
  "user_query": "스토리도 알려줘",
  "conversation_state": {
    "active_entity": "푸리나",
    "active_entity_type": "avatar",
    "active_topic": "profile",
    "last_route": "basic_lookup",
    "last_intent": "character_basic_info"
  }
}
```

---

## 6. debug 출력 제안

후속 질문을 처리했는지 확인하려면 상태 출력이 필요하다.

예시:

```text
[route=summary | intent=character_story_summary | parser=llm | style=default | context=last_entity:푸리나]
```

또는:

```text
[route=source_reader | intent=show_evidence | parser=llm | style=evidence | context=last_answer]
```

---

## 7. 완료 기준

```text
1. 완료: `푸리나 알려줘` 이후 `스토리도 알려줘`가 푸리나 대상 후속 질문으로 해석된다.
2. 완료: `푸리나 알려줘` 이후 `근거는?`이 직전 답변의 evidence 요청으로 해석된다.
3. 완료: `안회광 알려줘` 이후 `R1부터 R5까지 보여줘`가 안개를 가르는 회광 detail 요청으로 해석된다.
4. 완료: terminal status line과 route metadata에서 context 사용 여부가 보인다.
5. 완료: conversation state가 없어도 기존 단일 질문은 깨지지 않는다.
```

---

## 8. 주의 사항

처음부터 장기 메모리를 구현하지 않는다.

초기 목표는 다음만 해결하는 것이다.

```text
직전 대상 기억
직전 주제 기억
직전 route/intent 기억
후속 질문의 생략 대상 복원
```

장기 사용자 선호, 연구 메모리, workspace memory는 이 기능이 안정화된 뒤에 붙인다.
