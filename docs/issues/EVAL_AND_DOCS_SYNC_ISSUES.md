# Issue: 평가셋과 문서 상태를 새 대화형 QA 방향에 맞게 정리

Status: historical issue note. Current docs navigation is controlled by
`docs/README.md`.

작성일: 2026-06-28  
권장 위치: `docs/issues/EVAL_AND_DOCS_SYNC_ISSUES.md`

## 1. 문제 요약

현재 코드와 문서, 평가셋 사이에 기준이 서로 어긋나는 부분이 있다.

프로젝트는 이미 로컬 LLM, semantic parser, basic QA, Source Reader 일부를 갖추고 있다. 하지만 일부 문서는 아직 이전 단계 기준으로 작성되어 있고, 평가셋은 새 대화형 UX보다 기존의 정형 dump형 답변을 강제하는 경향이 있다.

이 상태에서는 Codex가 어느 기준에 맞춰 구현해야 하는지 혼란스러울 수 있다.

v0.6.2~v0.6.4에서 이 문서의 핵심 항목 중 일부는 반영됐다.

```text
반영됨:
- answer_evaluation_set.json에 requested_style/context/unsupported_reason/plan_intent 기대값 추가
- history 기반 ConversationState 평가 지원
- weapon default/detail 케이스 분리
- unsupported guide/meta 요청 route=unsupported로 변경
- `docs/implementation/ROADMAP_V2_IMPLEMENTATION_NOTES.md` 최신화

남음:
- semantic/parser/style/context 평가셋의 파일 분리
- README/상위 문서 전체 동기화
- summary/analysis/research writer 평가셋
```

---

## 2. 문서 상태 문제

### 2.1 README와 ROADMAP 불일치

README는 프로젝트가 v0.6 단계이며, 로컬 Ollama Qwen3 기반 정답형 QA 초안 생성까지 포함한다고 설명한다.

반면 기존 `docs/ROADMAP.md`는 프로젝트를 v0.5 상태로 설명하고, 실제 LLM 답변 생성이 아직 없다고 적고 있을 수 있다.

이 불일치는 다음 문제를 만든다.

```text
1. 현재 구현 상태를 잘못 판단하게 된다.
2. Codex가 이미 구현된 기능을 미구현으로 오해할 수 있다.
3. 다음 우선순위가 검색 고도화인지 대화형 QA인지 헷갈린다.
```

---

## 3. 평가셋 문제

### 3.1 기존 평가셋은 dump형 답변을 정답으로 강제함

예를 들어 무기 정보 질문에서 `R1:`과 `R5:`가 필수 fragment로 들어가 있으면, 기본 질문에서도 제련별 수치를 전부 출력해야 평가를 통과한다.

하지만 새 UX 방향에서는 다음처럼 구분해야 한다.

```text
안회광 알려줘
→ default style
→ 핵심 요약 중심
→ R1~R5 전체 출력은 필수 아님

안회광 R1부터 R5까지 보여줘
→ detail style
→ R1~R5 전체 출력 필수
```

즉 평가셋이 새 UX를 방해하지 않도록 style-aware 평가로 바뀌어야 한다.

---

## 4. unsupported route 기준 문제

현재 일부 unsupported 케이스는 route가 `basic_lookup` 또는 `analysis`로 남아 있고 intent만 unsupported가 될 수 있다.

예시:

```text
피슬 성유물 추천해줘
나선비경 티어 알려줘
```

이런 질문은 공식 DB 정답형 조회가 아니므로, 더 명확한 route/intent가 필요하다.

권장 구조:

```json
{
  "route": "unsupported",
  "intent": "guide_or_meta_request",
  "unsupported_reason": "unofficial_strategy_request"
}
```

또는 route enum에 `unsupported`를 추가하기 어렵다면 최소한 다음 필드를 둔다.

```json
{
  "route": "analysis",
  "intent": "unsupported",
  "unsupported_reason": "unofficial_strategy_request"
}
```

하지만 장기적으로는 `unsupported`도 명시적 route가 되는 편이 좋다.

---

## 5. 새 평가셋 구조 제안

평가셋을 하나로만 두지 말고 목적별로 분리한다.

```text
config/answer_evaluation_set.json
config/semantic_parser_evaluation_set.json
config/conversation_context_evaluation_set.json
config/answer_style_evaluation_set.json
config/unsupported_policy_evaluation_set.json
```

---

## 6. Semantic Parser 평가셋

예시:

```json
[
  {
    "id": "furina_basic_summary",
    "query": "푸리나에 대해서 요약해줘",
    "expected_route": "basic_lookup",
    "expected_intent": "character_basic_info",
    "expected_entity": "푸리나",
    "expected_style": "brief"
  },
  {
    "id": "furina_story_summary",
    "query": "푸리나 스토리 요약해줘",
    "expected_route": "summary",
    "expected_intent": "character_story_summary",
    "expected_entity": "푸리나"
  },
  {
    "id": "mistsplitter_default",
    "query": "안회광 알려줘",
    "expected_route": "basic_lookup",
    "expected_intent": "weapon_basic_info",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "default"
  },
  {
    "id": "mistsplitter_detail",
    "query": "안회광 R1부터 R5까지 보여줘",
    "expected_route": "basic_lookup",
    "expected_intent": "weapon_basic_info",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "detail"
  }
]
```

---

## 7. Conversation Context 평가셋

예시:

```json
[
  {
    "id": "furina_followup_story",
    "history": [
      {
        "user": "푸리나 알려줘",
        "active_entity": "푸리나",
        "active_topic": "profile"
      }
    ],
    "query": "스토리도 알려줘",
    "expected_route": "summary",
    "expected_intent": "character_story_summary",
    "expected_entity": "푸리나",
    "expected_context_used": true
  },
  {
    "id": "mistsplitter_followup_refinements",
    "history": [
      {
        "user": "안회광 알려줘",
        "active_entity": "안개를 가르는 회광",
        "active_topic": "weapon_basic_info"
      }
    ],
    "query": "R1부터 R5까지 보여줘",
    "expected_route": "basic_lookup",
    "expected_intent": "weapon_basic_info",
    "expected_entity": "안개를 가르는 회광",
    "expected_style": "detail",
    "expected_context_used": true
  }
]
```

---

## 8. Answer Style 평가셋

예시:

```json
[
  {
    "id": "mistsplitter_default_no_dump",
    "query": "안회광 알려줘",
    "expected_style": "default",
    "required_fragments": [
      "안개를 가르는 회광",
      "5성 한손검",
      "치명타 피해",
      "무절"
    ],
    "forbidden_fragments": [
      "R2:",
      "R3:",
      "R4:",
      "R5:"
    ]
  },
  {
    "id": "mistsplitter_detail_dump",
    "query": "안회광 R1부터 R5까지 보여줘",
    "expected_style": "detail",
    "required_fragments": [
      "R1:",
      "R5:"
    ]
  }
]
```

---

## 9. 문서 정리 제안

### 9.1 새 문서 추가

권장 추가 문서:

```text
docs/VISION_GROUNDED_CONVERSATIONAL_LORE_AI.md
docs/issues/LLM_SEMANTIC_PARSER_PRIORITY.md
docs/issues/CONVERSATION_STATE_FOLLOWUP.md
docs/issues/GROUNDED_WRITER_STYLE_CONTROLLER.md
docs/issues/EVAL_AND_DOCS_SYNC_ISSUES.md
```

### 9.2 기존 문서 업데이트

업데이트 필요 후보:

```text
README.md
docs/ROADMAP.md
docs/ANSWER_ROUTING_DESIGN.md
docs/PROJECT_STRUCTURE.md
```

### 9.3 ROADMAP 정리

기존 ROADMAP은 v0.5 중심이면 다음 중 하나로 처리한다.

```text
1. ROADMAP.md를 최신 v0.6.x~v1.0 기준으로 교체
2. 기존 문서를 ROADMAP_LEGACY.md로 이동
3. 새 구현 노트를 `docs/implementation/ROADMAP_V2_IMPLEMENTATION_NOTES.md`로 추가하고 README에서 링크
```

---

## 10. 완료 기준

```text
1. 부분 완료: ROADMAP_V2 implementation notes는 현재 단계에 맞게 갱신됐다. README 전체 동기화는 후속이다.
2. 후속: semantic parser 평가셋은 아직 별도 파일로 분리하지 않았다.
3. 부분 완료: conversation context 평가는 answer_evaluation_set.json의 history 케이스로 지원한다.
4. 부분 완료: answer style 평가는 answer_evaluation_set.json에서 default/detail/brief/evidence를 검증한다.
5. 완료: unsupported guide/meta request가 basic_lookup으로 오분류되지 않는다.
6. 완료: `docs/implementation/ROADMAP_V2_IMPLEMENTATION_NOTES.md`와 docs/issues 문서 기준으로 다음 우선순위를 이해할 수 있다.
```

---

## 11. 최종 판단

현재 프로젝트는 검색 코어와 basic QA를 넘어, 대화형 QA로 넘어가는 전환점에 있다.

따라서 평가셋과 문서도 기존의 “정형 조회가 맞는가”만 보는 기준에서 다음 기준으로 확장되어야 한다.

```text
질문을 자연스럽게 이해했는가?
후속 질문의 맥락을 복원했는가?
사용자 의도에 맞는 답변 깊이를 골랐는가?
DB facts 밖으로 나가지 않았는가?
지원하지 않는 요청을 정직하게 분류했는가?
```

이 기준이 정리되어야 이후 구현이 흔들리지 않는다.
