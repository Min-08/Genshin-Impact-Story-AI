# Grounded Conversational QA 설계 문서

작성일: 2026-06-28

## 1. 핵심 목표

이 문서는 원신 스토리 연구 AI를 단순 검색 CLI가 아니라, **DB 기반 정확성을 유지하면서 ChatGPT처럼 자연스럽게 질문을 이해하고 답변하는 대화형 연구 보조 도구**로 발전시키기 위한 설계 문서다.

현재 시스템은 Project Amber, TextMap, 검색 DB, basic lookup, local LLM rewriter가 연결되어 있다. 기술적으로는 작동하지만, 실제 사용자 경험은 아직 다음에 가깝다.

```text
정형 DB 조회기
+ 규칙 기반 라우터
+ 제한적인 LLM 문장 보정기
```

최종적으로 지향하는 형태는 다음이다.

```text
DB 기반 정확성
+ LLM 기반 자연어 이해
+ 근거 기반 답변 생성
+ 대화 컨텍스트 유지
+ 후속 질문 처리
```

즉, 목표는 LLM에게 원신 지식을 자유롭게 생성하게 하는 것이 아니라, **LLM을 대화 인터페이스와 표현 엔진으로 사용하고, 사실성은 DB와 validator가 통제하는 구조**를 만드는 것이다.

---

## 2. 현재 문제 인식

### 2.1 질문 이해가 규칙 기반에 갇혀 있음

현재 시스템은 다음 질문은 잘 처리한다.

```text
푸리나
푸리나 기본정보
푸리나의 기본 정보를 알려줘
안회광 알려줘
```

하지만 다음 질문은 사람이 보기에는 자연스러운 basic lookup 또는 짧은 summary 요청인데, 시스템은 제대로 처리하지 못할 수 있다.

```text
푸리나에 대해서 요약해줘
스토리도 알려줘
좀 더 자세히
그럼 얘는 포칼로스랑 무슨 관계야?
```

예를 들어 `푸리나에 대해서 요약해줘`는 사람이 보기에는 보통 다음 의미다.

```text
푸리나 기본 정보를 자연스럽게 요약해서 알려줘
```

하지만 현재 라우터가 `요약`이라는 단어를 강하게 보고 `summary` route로 보내면, 아직 summary writer가 구현되지 않았기 때문에 unsupported가 된다.

즉, 현재 문제는 단순히 라우팅 실패가 아니라 **사용자 자연어를 명령어처럼 해석하는 구조적 한계**다.

---

### 2.2 LLM이 켜져 있어도 답변이 AI답지 않음

현재 LLM은 주로 facts 기반 답변 앞에 붙는 짧은 문장 보정 역할에 가깝다. 그래서 출력이 다음처럼 정형화된다.

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

정보는 정확하지만, 사용자가 기대하는 대화형 답변과는 다르다.

사용자가 `안회광 알려줘`라고 했을 때 기대하는 출력은 대개 다음에 더 가깝다.

```text
안개를 가르는 회광은 5성 한손검이고, 치명타 피해 보조 옵션을 가진 무기야.

핵심 효과는 원소 피해 보너스와 「무절의 문장」 스택을 통해 자기 원소 피해를 올리는 구조야. 즉, 원소 피해를 자주 넣고 원소폭발을 활용하는 캐릭터에게 잘 맞는 무기라고 볼 수 있어.

제련별 수치는 길어서, 필요하면 R1~R5 전체 수치도 따로 펼쳐줄게.

출처: project_amber 공식 데이터 (ko)
```

따라서 문제는 단순히 LLM을 켜는 것이 아니라, **LLM이 답변 스타일과 정보 압축 방식을 담당하도록 구조를 바꾸는 것**이다.

---

## 3. 핵심 원칙

### 3.1 LLM은 답변의 사실 출처가 아니다

나쁜 구조:

```text
사용자 질문
→ LLM
→ 답변 생성
```

이 구조는 빠르게 챗봇처럼 보일 수 있지만, 원신 공식 데이터 기반 연구 도구라는 목표와 맞지 않는다. LLM이 공식 텍스트에 없는 관계, 설정, 추측을 자연스럽게 만들어낼 수 있기 때문이다.

좋은 구조:

```text
사용자 질문
→ LLM이 질문 의미를 해석
→ 시스템이 DB에서 facts/evidence 조회
→ LLM이 facts/evidence 안에서만 자연스럽게 답변
→ validator가 검증
→ 최종 답변
```

LLM은 자연어 이해와 표현을 담당하고, 사실성은 DB와 검증기가 담당한다.

---

### 3.2 정확성과 자연스러움의 책임 분리

```text
정확성:
- Project Amber
- TextMap
- SQLite search DB
- Source Reader
- Evidence Pack
- deterministic resolver
- validator

자연스러움:
- LLM semantic parser
- LLM grounded writer
- answer style controller
- conversation context resolver
```

이 책임 분리가 무너지면 시스템은 둘 중 하나로 망가진다.

```text
1. DB 조회기처럼 정확하지만 딱딱한 시스템
2. 챗봇처럼 자연스럽지만 근거가 약한 시스템
```

목표는 이 둘의 장점을 결합하는 것이다.

---

## 4. 권장 전체 파이프라인

최종 권장 구조는 다음과 같다.

```text
사용자 질문
→ command guard
→ ConversationState 로드
→ LLM semantic parser
→ AnswerPlan 생성
→ context resolver
→ deterministic resolver
→ DB facts/search/source reader/evidence pack 조회
→ grounded LLM writer
→ validator
→ 최종 답변
→ ConversationState 업데이트
```

각 단계의 역할은 다음과 같다.

| 단계 | 역할 |
|---|---|
| command guard | `exit`, `quit`, `q` 같은 터미널 명령 처리 |
| ConversationState | 이전 대상, 주제, 답변 범위, 출처 기억 |
| LLM semantic parser | 사용자 질문의 의도, 대상, 스타일, route를 JSON으로 해석 |
| AnswerPlan | 실행 가능한 답변 계획 |
| context resolver | `스토리도`, `더 자세히`, `그럼 얘는?` 같은 후속 질문 해석 |
| deterministic resolver | LLM이 추출한 엔티티와 route가 실제 DB에 맞는지 검증 |
| DB/evidence 조회 | 공식 데이터, 원문, 검색 결과, 근거 묶음 생성 |
| grounded writer | facts/evidence 안에서만 자연스럽게 답변 작성 |
| validator | 환각, facts 외 정보, 누락, 형식 위반 검사 |
| context update | 다음 질문을 위해 active entity/topic 저장 |

---

## 5. LLM Semantic Parser

### 5.1 목적

LLM semantic parser의 목적은 답변 생성이 아니다. 사용자의 자연어 질문을 실행 가능한 JSON 계획으로 바꾸는 것이다.

예시 입력:

```text
푸리나에 대해서 요약해줘
```

예상 출력:

```json
{
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "entity": {
    "name": "푸리나",
    "type": "character"
  },
  "requested_style": "brief_summary",
  "context_used": false,
  "needs_story_scope": false
}
```

여기서 중요한 점은 `요약해줘`라는 단어가 있다고 무조건 summary route로 보내면 안 된다는 것이다.

---

### 5.2 의미상 구분해야 하는 질문

```text
푸리나에 대해서 요약해줘
→ basic_lookup / character_basic_info / brief_summary

푸리나 스토리 요약해줘
→ summary / character_story_summary

푸리나와 포칼로스 관계 알려줘
→ analysis / character_relation

푸리나가 천리랑 관련 있다는 근거 찾아줘
→ research 또는 analysis

푸리나 원문 보여줘
→ source_reader / raw_source
```

즉 parser는 단어 단위가 아니라, 다음을 함께 판단해야 한다.

```text
1. 사용자가 묻는 대상
2. 대상의 종류
3. 원하는 정보 범위
4. 답변 스타일
5. 현재 구현된 route로 처리 가능한지
6. 이전 대화 컨텍스트를 사용해야 하는지
```

---

### 5.3 AnswerPlan 예시

```json
{
  "route": "basic_lookup",
  "intent": "weapon_basic_info",
  "entity": {
    "name": "안개를 가르는 회광",
    "type": "weapon"
  },
  "requested_style": "default",
  "detail_level": "medium",
  "include_raw_values": false,
  "include_source": true,
  "context_used": false,
  "unsupported_reason": null
}
```

---

## 6. ConversationState 설계

### 6.1 ConversationState가 필요한 이유

대화형 AI에서는 사용자가 매번 전체 질문을 쓰지 않는다.

예시:

```text
사용자: 푸리나 알려줘
AI: 푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야...

사용자: 스토리도 알려줘
```

두 번째 질문은 독립적으로 보면 대상이 없다. 하지만 대화 맥락에서는 다음 뜻이다.

```text
푸리나의 스토리도 알려줘
```

이 처리를 위해 ConversationState가 필요하다.

---

### 6.2 최소 상태 구조

초기 구현은 복잡하게 하지 말고 다음 정도면 충분하다.

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
  "last_answer_scope": "profile",
  "last_sources": [
    "project_amber:character:furina"
  ],
  "last_language": "ko",
  "turn_count": 1
}
```

---

### 6.3 후속 질문 처리 예시

#### 예시 1: 스토리도 알려줘

입력:

```text
스토리도 알려줘
```

현재 context:

```json
{
  "active_entity": {
    "name": "푸리나",
    "type": "character"
  },
  "active_topic": "profile"
}
```

해석 결과:

```json
{
  "resolved_query": "푸리나의 스토리를 알려줘",
  "route": "summary",
  "intent": "character_story_summary",
  "entity": {
    "name": "푸리나",
    "type": "character"
  },
  "context_used": true,
  "requested_style": "natural_summary"
}
```

---

#### 예시 2: 더 자세히

입력:

```text
더 자세히
```

해석 결과:

```json
{
  "resolved_query": "푸리나 기본정보를 더 자세히 알려줘",
  "route": "basic_lookup",
  "intent": "character_basic_info",
  "entity": {
    "name": "푸리나",
    "type": "character"
  },
  "context_used": true,
  "requested_style": "detail"
}
```

---

#### 예시 3: 근거는?

입력:

```text
근거는?
```

해석 결과:

```json
{
  "resolved_query": "방금 답변의 공식 원문 근거를 보여줘",
  "route": "source_reader",
  "intent": "show_evidence",
  "entity": {
    "name": "푸리나",
    "type": "character"
  },
  "context_used": true,
  "requested_style": "evidence"
}
```

---

#### 예시 4: 그럼 포칼로스랑 관계는?

입력:

```text
그럼 포칼로스랑 관계는?
```

해석 결과:

```json
{
  "resolved_query": "푸리나와 포칼로스의 관계를 공식 근거 중심으로 설명해줘",
  "route": "analysis",
  "intent": "character_relation_analysis",
  "entities": [
    {
      "name": "푸리나",
      "type": "character"
    },
    {
      "name": "포칼로스",
      "type": "character_or_concept"
    }
  ],
  "context_used": true,
  "requested_style": "grounded_analysis"
}
```

---

## 7. 답변 스타일 제어

### 7.1 왜 답변 모드가 필요한가

현재 basic lookup은 모든 정보를 한 번에 펼치는 경향이 있다.

하지만 사용자의 질문은 같은 `알려줘`라도 기대하는 답변 길이가 다를 수 있다.

```text
푸리나 알려줘
→ 핵심 프로필 중심

푸리나 자세히 알려줘
→ 프로필 + 칭호 + 운명의 자리 + 생일 + 소개문 + CV

푸리나 원문 그대로 보여줘
→ raw source

푸리나 스토리 요약해줘
→ 캐릭터 스토리/퀘스트 범위 요약

푸리나랑 포칼로스 관계 근거 중심으로 알려줘
→ 분석형 답변
```

따라서 writer는 출력 모드를 가져야 한다.

---

### 7.2 출력 모드

| 모드 | 목적 | 예시 질문 |
|---|---|---|
| brief | 한두 문장 요약 | `푸리나 짧게 알려줘` |
| default | 핵심 정보 + 중요한 세부사항 | `푸리나 알려줘` |
| detail | 가능한 공식 필드 자세히 출력 | `푸리나 자세히 알려줘` |
| raw | 원문/DB 필드 그대로 출력 | `원문 보여줘` |
| evidence | 근거와 출처 중심 | `근거는?` |
| analysis | 관계/의미 분석 | `포칼로스랑 관계는?` |
| research | 가설/반례/신뢰도 비교 | `페이몬 정체 추측해줘` |

---

### 7.3 무기 답변 압축 예시

질문:

```text
안회광 알려줘
```

현재 출력은 R1~R5를 전부 펼치지만, 기본 모드에서는 다음처럼 답하는 것이 더 자연스럽다.

```text
안개를 가르는 회광은 5성 한손검이고, 보조 속성은 치명타 피해야.

핵심 효과는 모든 원소 피해 보너스를 얻고, 「무절의 문장」 스택에 따라 자신의 원소 타입 피해 보너스가 추가로 증가하는 구조야. 쉽게 말하면 원소 피해를 자주 넣고 원소폭발을 활용하는 캐릭터에게 잘 맞는 무기라고 볼 수 있어.

제련별 수치는 꽤 길어서, 원하면 R1~R5 수치를 따로 펼쳐줄게.

출처: project_amber 공식 데이터 (ko)
```

사용자가 다음처럼 물으면:

```text
R1부터 R5까지 수치도 보여줘
```

그때 detail 모드로 전환한다.

---

## 8. Grounded LLM Writer

### 8.1 writer의 역할

Grounded writer는 facts와 evidence 안에서만 답변을 자연스럽게 작성한다.

입력 예시:

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

출력 예시:

```text
푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야. 공식 데이터 기준 칭호는 「멈추지 않는 독무」이고, 운명의 자리는 코레고스자리야.

생일은 10월 13일로 기록되어 있고, 돌파 보너스는 치명타 확률이야.

출처: project_amber 공식 데이터 (ko)
```

---

### 8.2 writer 금지 사항

writer는 다음을 하면 안 된다.

```text
1. facts에 없는 설정 추가
2. 공식 데이터와 해석을 섞기
3. 스토리 추측을 기본정보처럼 말하기
4. 출처 없는 관계 단정
5. 사용자 질문보다 과도하게 긴 raw dump 출력
6. validator를 우회하기 위한 애매한 표현 사용
```

---

## 9. Validator 설계

### 9.1 validator가 필요한 이유

LLM writer를 자연스럽게 만들수록 환각 가능성이 생긴다. 따라서 writer 이후 검증 단계가 필요하다.

validator는 다음을 검사한다.

```text
1. facts에 없는 고유명사 추가 여부
2. facts에 없는 관계 단정 여부
3. 출처 없는 스토리 해석 포함 여부
4. 필수 fragment 누락 여부
5. requested_style 위반 여부
6. unsupported intent를 지원하는 것처럼 말했는지
```

---

### 9.2 검증 실패 시 처리

검증 실패 시 바로 사용자에게 보여주지 않고, 다음 중 하나를 수행한다.

```text
1. writer에게 재작성 요청
2. 더 보수적인 template writer로 fallback
3. "현재 공식 데이터 기준으로는 확인되지 않습니다" 형태로 제한 답변
```

---

## 10. 단계별 구현 우선순위

### v0.6.3 - LLM Semantic Parser 기본 ON

목표:

```text
모든 일반 질문을 먼저 LLM semantic parser에 보내고, JSON AnswerPlan을 생성한다.
```

작업:

```text
1. command guard를 제외한 질문은 LLM parser로 보낸다.
2. parser 출력 JSON schema를 고정한다.
3. route, intent, entity, requested_style, context_reference를 포함한다.
4. JSON 파싱 실패 시 기존 deterministic router로 fallback한다.
5. parser 평가셋을 만든다.
```

완료 기준:

```text
푸리나에 대해서 요약해줘
→ basic_lookup / character_basic_info / brief_summary

안회광 알려줘
→ basic_lookup / weapon_basic_info / default

스토리도 알려줘
→ context_reference 필요로 분류
```

---

### v0.6.4 - ConversationState v0.1

목표:

```text
직전 active entity와 topic을 기억하고 후속 질문을 해석한다.
```

작업:

```text
1. ChatSession 또는 ConversationState 모델을 만든다.
2. active_entity, active_topic, last_route, last_intent를 저장한다.
3. `스토리도`, `더 자세히`, `근거는?` 같은 follow-up query를 처리한다.
4. context_used 여부를 debug 출력에 표시한다.
```

완료 기준:

```text
질문> 푸리나 알려줘
질문> 스토리도 알려줘

두 번째 질문이 푸리나의 스토리 요청으로 해석된다.
```

---

### v0.6.5 - Answer Style Controller

목표:

```text
질문 의도에 따라 brief/default/detail/raw/evidence 출력 모드를 선택한다.
```

작업:

```text
1. requested_style enum을 추가한다.
2. basic lookup 출력에서 default/detail을 분리한다.
3. 무기 R1~R5 전체 출력은 detail 또는 explicit request에서만 보여준다.
4. default 답변은 핵심 정보 중심으로 압축한다.
```

완료 기준:

```text
안회광 알려줘
→ 핵심 요약 + "원하면 R1~R5 수치도 보여줄게"

안회광 R1부터 R5까지 보여줘
→ 전체 수치 출력
```

---

### v0.6.6 - Grounded Writer v1

목표:

```text
facts 기반 정확성을 유지하면서 답변을 자연스럽게 작성한다.
```

작업:

```text
1. writer 입력을 user_query, answer_plan, facts, evidence, source_policy로 정리한다.
2. LLM writer는 facts/evidence 외 내용을 쓰지 못하게 한다.
3. source label을 항상 유지한다.
4. writer 실패 시 deterministic template로 fallback한다.
```

완료 기준:

```text
LLM 답변이 자연스러워지되, 공식 데이터에 없는 내용을 추가하지 않는다.
```

---

### v0.6.7 - Writer Validator

목표:

```text
LLM writer의 자연스러운 답변이 facts를 벗어나지 않게 검증한다.
```

작업:

```text
1. facts 기반 allowed token/entity set을 만든다.
2. 출력에서 facts에 없는 고유명사/관계 표현을 검사한다.
3. 필수 fragment 누락 여부를 검사한다.
4. 실패 시 재작성 또는 template fallback한다.
```

완료 기준:

```text
자연스러운 답변과 deterministic correctness가 동시에 유지된다.
```

---

## 11. 최종 대화 UX 예시

### 11.1 기본 조회

```text
질문> 푸리나 알려줘

푸리나는 폰타인 출신의 5성 물 원소 한손검 캐릭터야. 공식 데이터 기준 칭호는 「멈추지 않는 독무」이고, 운명의 자리는 코레고스자리야.

생일은 10월 13일로 기록되어 있고, 돌파 보너스는 치명타 확률이야.

출처: project_amber 공식 데이터 (ko)
```

---

### 11.2 후속 질문

```text
질문> 스토리도 알려줘

푸리나의 스토리 쪽으로 이어서 볼게.

이 질문은 단순 캐릭터 프로필이 아니라 캐릭터 스토리, 마신임무, 관련 대사 범위를 함께 봐야 하는 summary/analysis 영역이야. 공식 근거 기반으로 정리하려면 먼저 푸리나와 관련된 스토리 문서 범위를 확정하고, 그 안에서 사건 순서와 핵심 주제를 분리하는 방식이 좋아.

현재 summary route가 연결되면 다음 순서로 답할 수 있어.

1. 관련 공식 텍스트 범위 확정
2. 원문 근거 수집
3. 사건 순서 요약
4. 공식 사실과 해석 분리
5. 필요한 경우 반례 또는 불확실한 부분 표시
```

---

### 11.3 세부 수치 요청

```text
질문> 안회광 알려줘

안개를 가르는 회광은 5성 한손검이고, 보조 속성은 치명타 피해야.

핵심 효과는 모든 원소 피해 보너스를 얻고, 「무절의 문장」 스택에 따라 자신의 원소 타입 피해 보너스가 추가로 증가하는 구조야. 기본 답변에서는 핵심 구조만 요약하고, 제련별 수치는 필요할 때 따로 펼치는 게 좋아.

출처: project_amber 공식 데이터 (ko)
```

```text
질문> R1부터 R5까지 보여줘

좋아. 방금 말한 안개를 가르는 회광의 제련별 효과를 공식 데이터 기준으로 펼쳐볼게.

R1: ...
R2: ...
R3: ...
R4: ...
R5: ...

출처: project_amber 공식 데이터 (ko)
```

---

## 12. 구현 시 주의할 점

### 12.1 no-LLM 경로는 버리면 안 됨

LLM parser와 writer를 기본 ON으로 두더라도 no-LLM 경로는 유지해야 한다.

이유:

```text
1. CI 테스트 가능
2. 로컬 LLM 오류 시 fallback
3. deterministic correctness 검증
4. 정형 QA 품질 보장
```

따라서 최종 구조는 다음이 되어야 한다.

```text
LLM ON:
자연어 UX + grounded writer

LLM OFF:
정형 lookup + template answer
```

---

### 12.2 LLM parser 결과를 그대로 믿으면 안 됨

LLM이 `푸리나`를 캐릭터라고 판단해도 시스템은 반드시 DB에서 확인해야 한다.

```text
LLM output:
entity = 푸리나
type = character

resolver:
DB에 존재하는가?
canonical id가 있는가?
지원 가능한 intent인가?
```

검증에 실패하면 후보를 제시하거나 unsupported로 처리한다.

---

### 12.3 컨텍스트는 작게 시작해야 함

처음부터 장기 메모리, 사용자 취향, 연구 노트까지 넣으면 복잡도가 커진다.

초기 ConversationState는 다음만 저장한다.

```text
1. active_entity
2. active_topic
3. last_route
4. last_intent
5. last_sources
6. last_answer_style
```

이 정도만으로도 `스토리도`, `더 자세히`, `근거는?` 같은 핵심 후속 질문을 처리할 수 있다.

---

## 13. 최종 판단

현재 프로젝트는 이미 DB, 검색, basic lookup, local LLM 연결이 되어 있으므로 기반은 충분하다. 다음 병목은 검색 정확도보다 **대화형 답변 계획과 자연어 UX**다.

가장 중요한 전환은 다음 세 가지다.

```text
1. LLM Semantic Parser
   - 사용자의 자연어 질문을 AnswerPlan으로 변환

2. ConversationState
   - 이전 대상과 주제를 기억해 후속 질문 처리

3. Grounded LLM Writer
   - DB facts와 evidence 안에서만 자연스럽게 답변
```

이 세 가지가 들어가면 시스템은 단순 검색 CLI에서 벗어나, 공식 데이터 기반의 대화형 원신 스토리 연구 AI로 발전할 수 있다.

반대로 이 세 가지 없이 검색 기능만 늘리면, 검색 정확도는 좋아져도 사용자는 여전히 명령어처럼 질문해야 한다. 목표가 ChatGPT 같은 대화형 연구 보조 도구라면, 지금 다음 단계는 `AnswerPlan + ConversationState + grounded writer`다.
