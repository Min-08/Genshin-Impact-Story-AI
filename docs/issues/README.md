# docs/issues 추가 권장 문서 묶음

작성일: 2026-06-28

이 폴더는 `Genshin-Impact-Story-AI` 프로젝트의 `docs/issues/`에 넣기 위한 이슈 문서 초안이다.

## 포함 문서

1. `LLM_SEMANTIC_PARSER_PRIORITY.md`
   - LLM semantic parser를 AnswerPlan 후보 생성에 쓰되 hard guard와 DB resolver 뒤에서 검증하는 작업.

2. `CONVERSATION_STATE_FOLLOWUP.md`
   - `스토리도 알려줘`, `근거는?`, `더 자세히` 같은 후속 질문을 처리하기 위한 ConversationState v0.1.

3. `GROUNDED_WRITER_STYLE_CONTROLLER.md`
   - facts 기반 정확성을 유지하면서 답변을 자연스럽게 만들기 위한 grounded writer와 style controller.

4. `EVAL_AND_DOCS_SYNC_ISSUES.md`
   - 평가셋과 문서 상태를 새 대화형 QA 방향에 맞게 정리하는 작업.

## 권장 적용 순서

```text
1. 완료된 v0.6.2~v0.6.4 범위 확인
2. Source Reader / Evidence Pack 통합
3. Summary Scope resolver
4. Analysis claim writer
5. Research loop v1
```

핵심은 새 기능을 무작정 늘리는 것이 아니라, 이미 있는 검색/QA 기반 위에 자연어 의미 파악, 후속 질문 맥락, 답변 스타일 제어를 DB correctness가 깨지지 않는 방식으로 얹는 것이다.
