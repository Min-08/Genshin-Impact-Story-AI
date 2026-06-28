# Issue: Grounded Writer와 Answer Style Controller 도입

작성일: 2026-06-28  
권장 위치: `docs/issues/GROUNDED_WRITER_STYLE_CONTROLLER.md`

## 1. 문제 요약

현재 LLM은 켜져 있어도 답변 전체를 자연스럽게 재구성하지 않는다. 실제 역할은 템플릿 답변 앞에 짧은 리드 문장 하나를 붙이는 것에 가깝다.

그 결과 답변은 정확하지만 정형 DB 출력처럼 보인다.

예시:

```text
공식 데이터 기준 무기 정보입니다.
안개를 가르는 회광은 5성 한손검입니다.

설명은 ...
보조 속성은 ...
무기 효과는 ...
R1: ...
R2: ...
R3: ...
R4: ...
R5: ...
```

사용자가 `안회광 알려줘`라고 했을 때 기본적으로 기대하는 것은 전체 raw dump가 아니라 핵심 요약이다.

---

## 2. 목표

DB 기반 facts는 유지하면서, 답변 표현은 사용자의 요청 깊이에 맞게 자연스럽게 조절한다.

핵심 목표:

```text
facts/evidence는 DB가 제공한다.
writer는 facts/evidence 안에서만 자연스럽게 답한다.
validator는 facts 밖으로 벗어난 출력을 막는다.
```

v0.6.3 기준으로 `requested_style`과 template writer의 최소 정책은 구현됐다. 다만 완전한 LLM 기반 grounded writer는 아직 후속 과제이며, 현재 LLM rewriter는 보수적 fallback 성격을 유지한다.

---

## 3. 현재 rewriter의 한계

현재 LLM rewriter는 다음과 같은 제한이 강하다.

```text
- 한 문장만 생성
- 숫자 금지
- 고유명사 금지
- 사실 요약 금지
- draft 앞에 lead sentence만 추가
```

이 구조는 안전하지만, 사용자가 기대하는 ChatGPT식 자연어 답변을 만들기 어렵다.

따라서 기존 rewriter는 fallback 또는 conservative mode로 유지하고, 별도의 grounded writer를 추가하는 것이 좋다.

---

## 4. Answer Style Controller

### 4.1 필요한 스타일

`requested_format`과 별개로 `requested_style`을 추가한다.

```text
brief
default
detail
raw
evidence
analysis
research
```

### 4.2 스타일별 의미

| style | 의미 | 예시 |
|---|---|---|
| brief | 한두 문장 요약 | `푸리나 짧게 알려줘` |
| default | 핵심 정보 중심 | `푸리나 알려줘`, `안회광 알려줘` |
| detail | 가능한 세부 정보 출력 | `자세히 알려줘`, `R1부터 R5까지 보여줘` |
| raw | 원문/DB 필드 중심 | `원문 그대로 보여줘` |
| evidence | 근거와 출처 중심 | `근거는?` |
| analysis | 관계/의미 분석 | `포칼로스랑 관계는?` |
| research | 가설/반례/신뢰도 비교 | `페이몬 정체 추측해줘` |

---

## 5. 무기 답변 정책

### 5.1 default

질문:

```text
안회광 알려줘
```

기대 답변:

```text
안개를 가르는 회광은 5성 한손검이고, 보조 속성은 치명타 피해야.

핵심 효과는 모든 원소 피해 보너스를 얻고, 「무절의 문장」 스택에 따라 자신의 원소 타입 피해 보너스가 추가로 증가하는 구조야.

제련별 수치는 길어서, 원하면 R1~R5 전체 수치를 따로 보여줄게.

출처: project_amber 공식 데이터 (ko)
```

### 5.2 detail

질문:

```text
안회광 R1부터 R5까지 보여줘
```

기대 답변:

```text
안개를 가르는 회광의 제련별 효과를 공식 데이터 기준으로 펼쳐볼게.

R1: ...
R2: ...
R3: ...
R4: ...
R5: ...

출처: project_amber 공식 데이터 (ko)
```

---

## 6. 캐릭터 답변 정책

### 6.1 default

질문:

```text
푸리나 알려줘
```

기대 답변:

```text
푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야. 공식 데이터 기준 칭호는 「멈추지 않는 독무」이고, 운명의 자리는 코레고스자리야.

생일은 10월 13일로 기록되어 있고, 돌파 보너스는 치명타 확률이야.

출처: project_amber 공식 데이터 (ko)
```

### 6.2 brief

질문:

```text
푸리나에 대해서 요약해줘
```

기대 답변:

```text
푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야. 공식 데이터 기준으로는 「멈추지 않는 독무」라는 칭호와 코레고스자리 운명의 자리를 가진 캐릭터로 기록되어 있어.

출처: project_amber 공식 데이터 (ko)
```

### 6.3 detail

질문:

```text
푸리나 자세히 알려줘
```

기대 답변:

```text
프로필, 무기, 원소, 지역, 운명의 자리, 생일, 돌파 보너스, 칭호, 소개문, CV까지 출력한다.
```

---

## 7. Grounded Writer 입력 계약

writer에는 반드시 facts와 answer plan을 함께 전달한다.

```json
{
  "user_query": "푸리나 알려줘",
  "answer_plan": {
    "route": "basic_lookup",
    "intent": "character_basic_info",
    "requested_style": "default"
  },
  "facts": {
    "name": "푸리나",
    "rank": 5,
    "element": "물",
    "weapon_type": "한손검",
    "region": "폰타인",
    "constellation": "코레고스자리",
    "birthday": "10월 13일",
    "title": "멈추지 않는 독무",
    "special_prop": "치명타 확률"
  },
  "source_policy": {
    "allowed_sources": ["project_amber"],
    "allow_inference": false
  }
}
```

writer는 facts에 없는 내용을 공식 사실처럼 추가하면 안 된다.

---

## 8. Validator 정책

Grounded writer를 도입하면 validator도 style-aware가 되어야 한다.

현재처럼 모든 refinement text를 항상 required fragment로 검사하면, default 답변의 핵심 요약이 실패할 수 있다.

### 8.1 default validator

```text
이름
등급
타입
핵심 속성
효과 이름
출처
```

### 8.2 detail validator

```text
default 필수 요소
+ R1
+ R5
+ 각 refinement 핵심 수치
```

### 8.3 raw validator

```text
원문 필드 보존
수치 누락 최소화
```

---

## 9. 구현 제안

### 9.0 현재 구현 상태

```text
완료:
- requested_style: brief/default/detail/raw/evidence/analysis/research
- 무기 default: R1 기준 효과만 출력, R2~R5 전체 dump 금지
- 무기 detail/raw/table: R1~R5 출력
- 캐릭터 brief: 기본 프로필 중심의 짧은 답변
- validator: requested_style에 따라 필수 fragment 범위 조절

후속:
- write_grounded_answer_with_ollama()
- claim/source 기반 writer
- raw style 전용 writer
- evidence style의 Source Reader deep integration
```

### 9.1 새 함수 추가

```python
def write_grounded_answer_with_ollama(
    *,
    user_query: str,
    facts: dict[str, Any],
    answer_plan: dict[str, Any],
    draft_answer: str,
    model: str,
) -> dict[str, Any]:
    ...
```

### 9.2 기존 rewriter 유지

기존 `rewrite_answer_with_ollama()`는 다음 용도로 유지한다.

```text
- LLM writer 실패 시 fallback
- strict/conservative mode
- no-risk answer mode
```

### 9.3 weapon writer 분리

`draft_weapon_answer()`에서 기본 paragraph 모드에 R1~R5를 무조건 포함하지 않는다.

```text
default: 핵심 요약
detail: R1~R5 포함
raw: 전체 필드
```

---

## 10. 완료 기준

```text
1. 완료: `안회광 알려줘`는 R1~R5를 기본으로 전부 dump하지 않는다.
2. 완료: `안회광 R1부터 R5까지 보여줘`는 R1~R5를 출력한다.
3. 완료: `푸리나에 대해서 요약해줘`는 짧은 basic profile 요약으로 답한다.
4. 부분 완료: 현재 validator는 facts 밖 숫자/이름/필수 fragment를 막는다. claim-level validator는 후속이다.
5. 완료: writer 실패 시 기존 template/rewrite 경로로 fallback한다.
6. 완료: answer evaluation이 style별 expected field로 통과한다.
```

---

## 11. 주의 사항

답변을 자연스럽게 만드는 것이 목표지만, LLM이 자유롭게 지식을 추가하게 해서는 안 된다.

```text
자연스러움은 허용한다.
환각은 허용하지 않는다.
공식 사실과 해석은 분리한다.
```
