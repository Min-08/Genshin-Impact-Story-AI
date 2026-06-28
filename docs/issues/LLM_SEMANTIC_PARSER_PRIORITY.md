# Issue: LLM Semantic Parser와 AnswerPlan Merge 안정화

작성일: 2026-06-28  
권장 위치: `docs/issues/LLM_SEMANTIC_PARSER_PRIORITY.md`

## 1. 문제 요약

현재 프로젝트에는 로컬 LLM 기반 semantic parser가 존재한다. 이 parser는 사용자의 자연어 의도를 읽는 데 유용하지만, 최종 route safety와 DB 기반 correctness를 결정하면 안 된다.

v0.6.2 기준 정책은 다음이다.

```text
LLM semantic parser는 AnswerPlan 후보를 만든다.
hard guard와 DB resolver는 그 후보를 검증하거나 기각한다.
```

그 결과 다음과 같은 자연어 질문이 사용자의 의도와 다르게 처리될 수 있다.

```text
질문: 푸리나에 대해서 요약해줘

사용자 의도:
푸리나의 기본 정보를 짧고 자연스럽게 요약해줘.

현재 발생 가능한 처리:
route=summary
intent=unsupported
```

이 문제는 단순 라우터 버그라기보다, 시스템이 아직 사용자의 자연어를 “대화”로 이해하지 못하고 “키워드 명령”처럼 해석하는 구조에서 나온다.

---

## 2. 목표

질문 의미 파악에는 LLM semantic parser를 사용하되, 실행 판단은 정규화된 AnswerPlan과 deterministic guard/resolver의 병합 결과로 한다.

핵심 목표는 다음이다.

```text
사용자 질문
→ command/greeting guard
→ unsupported strategy guard
→ deterministic entity resolver
→ LLM Semantic Parser로 AnswerPlan 후보 생성
→ route merge
→ 실행 가능 여부 판단
```

LLM은 답변을 생성하는 것이 아니라, 사용자의 질문을 실행 가능한 계획으로 해석해야 한다.
단, LLM이 `나선비경 티어 알려줘` 같은 요청을 `basic_lookup`으로 반환해도 hard guard가 이를 `unsupported`로 고정한다.

---

## 3. 현재 구조의 한계

현재 구조는 다음에 가깝다.

```text
사용자 질문
→ rule router
→ semantic parser
→ exact lookup
→ route merge
```

문제는 rule router가 `요약`, `정리`, `관계`, `가능성` 같은 키워드를 먼저 강하게 잡으면, LLM parser가 더 적절한 의도를 파악해도 최종 route를 뒤집기 어렵다는 점이다.

예시:

```text
푸리나에 대해서 요약해줘
```

여기서 `요약`이라는 단어만 보면 summary route가 맞아 보이지만, 실제로는 character basic lookup의 `brief` 스타일일 가능성이 높다.

---

## 4. 원하는 AnswerPlan

LLM parser는 다음과 같은 구조를 반환해야 한다.

```json
{
  "schema_version": "answer_plan.v0.1",
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "entities": [
    {
      "surface": "푸리나",
      "content_type_hint": "avatar",
      "confidence": 0.92
    }
  ],
  "requested_style": "brief",
  "detail_level": "low",
  "context_reference": null,
  "context_used": false,
  "needs_evidence": false,
  "needs_raw_source": false,
  "unsupported_reason": null,
  "confidence": 0.86
}
```

기존 `requested_format`은 출력 형식 중심이다.

```text
paragraph
bullet
table
short
long
```

하지만 대화형 QA에서는 이것만으로 부족하다. 다음과 같은 `requested_style`이 필요하다.

```text
brief
default
detail
raw
evidence
analysis
research
```

---

## 5. 대표 케이스

### 5.1 기본정보 요약

```text
입력:
푸리나에 대해서 요약해줘

기대:
route=basic_lookup
intent=character_basic_info
entity=푸리나
requested_style=brief
```

### 5.2 스토리 요약

```text
입력:
푸리나 스토리 요약해줘

기대:
route=summary
intent=character_story_summary
entity=푸리나
requested_style=default
```

### 5.3 관계 분석

```text
입력:
푸리나랑 포칼로스 관계는?

기대:
route=analysis
intent=character_relation_analysis
entities=[푸리나, 포칼로스]
requested_style=analysis
```

### 5.4 공략/티어 요청

```text
입력:
나선비경 티어 알려줘

기대:
route=unsupported
intent=guide_or_meta_request
unsupported_reason=unofficial_strategy_request
```

---

## 6. 구현 상태와 남은 작업

### 6.1 v0.6.2에서 완료된 항목

```text
AnswerPlan v0.1 추가
semantic_parse.v0.1 호환 유지
requested_style, needs_evidence, needs_raw_source, unsupported_reason 정규화
추천/티어/세팅/나선비경/공략 hard guard
summary/analysis/research writer 미구현 시 route_not_implemented 보존
```

### 6.2 `semantic.py` 확장

semantic parse schema는 `answer_plan.v0.1`에 가깝게 확장됐다.

추가할 필드:

```text
requested_style
detail_level
context_reference
context_used
needs_evidence
needs_raw_source
unsupported_reason
```

### 6.3 `route_answer_query()` 병합 정책

현재 병합 정책:

```text
1. command/greeting guard
2. unsupported strategy guard
3. deterministic entity resolver
4. LLM parser
5. fallback router
```

이 순서는 의도적이다. LLM parser를 더 앞에 두면 공략/티어/나선비경 요청이 다시 basic_lookup으로 승격될 수 있다.

### 6.4 남은 작업

```text
analysis/research용 세부 intent 확장
LLM parser 평가셋 분리
semantic parser에 ConversationState 요약 입력 제공
AnswerPlan schema를 별도 모델/문서로 고정
```

### 6.5 fallback 유지

LLM parser가 실패하면 기존 deterministic router를 사용한다.

fallback 조건:

```text
Ollama connection error
timeout
invalid JSON
schema validation failure
route enum mismatch
```

---

## 7. 완료 기준

```text
1. 완료: `푸리나에 대해서 요약해줘`가 summary/unsupported로 가지 않는다.
2. 완료: 해당 질문은 basic_lookup + character_basic_info + brief style로 처리된다.
3. 완료: `푸리나 스토리 요약해줘`는 summary + character_story_summary로 처리된다.
4. 완료: `나선비경 티어 알려줘`는 basic_lookup이 아니라 unsupported/guide 계열로 처리된다.
5. 완료: parser 실패 시 deterministic router로 fallback한다.
6. 부분 완료: debug/route metadata에서 parser가 보인다. 별도 개발자용 trace 출력은 후속 과제다.
```

---

## 8. 주의 사항

LLM parser를 도입했다고 해서 LLM을 믿고 바로 답변하면 안 된다.

```text
LLM은 의미를 해석한다.
DB는 사실을 검증한다.
Writer는 facts/evidence 안에서만 답한다.
Validator는 LLM 출력이 선을 넘지 못하게 한다.
```

이 원칙을 유지해야 DB 기반 정확성과 ChatGPT식 자연어 UX를 동시에 얻을 수 있다.
