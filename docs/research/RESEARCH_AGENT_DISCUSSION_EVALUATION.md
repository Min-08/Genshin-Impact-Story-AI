# Research Agent 추가 논의 평가

## 1. 문서 목적

이 문서는 원신 Lore Research Agent와 관련해 추가로 논의된 내용을 평가하고, 기존 프로젝트 문서에 반영할 때의 방향을 정리한다.

핵심 질문은 다음이다.

```text
이번 논의가 프로젝트 방향에 맞는가?
실제로 구현 가능한가?
기존 검색엔진 설계와 충돌하지 않는가?
어떤 순서로 문서화하고 구현해야 하는가?
```

결론부터 말하면, 이번 논의는 프로젝트의 최종 비전과 잘 맞는다.

다만 그대로 구현하면 범위가 너무 커질 수 있으므로, 초기에는 멀티 에이전트 구조를 실제 독립 agent 여러 개로 나누기보다 research loop 안의 역할 단위로 시작하는 것이 좋다.

---

## 2. 전체 평가

이번 논의의 핵심 방향은 타당하다.

```text
정답형 질문:
로컬 DB / 규칙 / 템플릿이 사실을 결정하고,
작은 LLM은 문장 풍성화만 담당한다.

연구형 질문:
LLM이 탐색 방향과 가설을 만들고,
검색엔진과 Source Reader가 공식 원문 근거를 고정한다.
```

이 역할 분리는 기존 프로젝트의 설계 원칙과 잘 맞는다.

기존 문서에서도 검색엔진은 공식 DB 탐색과 Evidence Pack 생성을 담당하고, LLM은 그 근거를 해석하는 계층으로 정의되어 있다. 이번 논의는 그 방향을 더 구체화해서, 특히 research route에서 필요한 읽기 도구와 능동형 탐색 구조를 명확히 했다.

종합 평가는 다음과 같다.

```text
방향성: 매우 좋음
비전 적합성: 높음
현재 프로젝트와의 연결성: 좋음
구현 난이도: 높음
초기 구현 그대로 따라가기: 위험
단계적으로 쪼개면: 현실적
```

---

## 3. 좋은 점

## 3.1 정답형 QA와 연구형 탐색의 분리

이번 논의에서 가장 중요한 장점은 정답형 질문과 연구형 질문을 분리했다는 점이다.

정답형 질문의 예:

```text
절연의 기치 효과 알려줘
푸리나가 누구야?
수메르 마신임무 요약해줘
```

이런 질문은 모델이 추론할 필요가 없다.

권장 구조:

```text
DB 조회
→ 구조화된 facts JSON 생성
→ 템플릿 답변 생성
→ 작은 LLM으로 문장 풍성화
→ validator 검사
```

연구형 질문의 예:

```text
파네스와 천리의 관계 가능성은?
세계수 기억 조작이 천리와 연결될 수 있어?
페이몬의 정체를 공식 근거 중심으로 다시 봐줘.
```

이런 질문은 정답이 DB에 직접 들어 있는 것이 아니라, 근거 수집과 가설 비교가 필요하다.

권장 구조:

```text
LLM이 탐색 계획 생성
→ 검색엔진이 공식 원문 후보 검색
→ Source Reader가 문맥 확장
→ Discovery Agent가 새 연결 후보 발견
→ Counter Agent가 반례 후보 탐색
→ Synthesizer가 가설별 보고서 작성
```

이 분리는 구현상 중요하다.

정답형 질문까지 research loop로 보내면 느리고 불안정해지고, 연구형 질문을 단순 검색으로 처리하면 프로젝트 비전이 제한된다.

---

## 3.2 문맥 단절 문제를 정확히 짚음

research route에서는 단순히 검색 hit 하나를 가져오는 것으로 부족하다.

중요한 단서는 검색된 문장의 앞뒤에 있을 수 있고, 같은 섹션이나 연결된 문서에 있을 수도 있다.

따라서 이번 논의에서 제안된 Reading Window 구조는 매우 중요하다.

```text
find_exact
→ read_window
→ expand_before / expand_after
→ read_section
→ read_document
→ read_neighbor_document
```

이 구조는 LLM이 원문을 읽으면서 필요할 때 문맥을 확장할 수 있게 한다.

핵심은 다음이다.

```text
find 도구가 아니라,
읽으면서 확장하는 원문 브라우저가 필요하다.
```

이 개념은 기존 검색엔진의 다음 단계로 자연스럽게 연결된다.

```text
현재:
chunk 검색 + Evidence Pack 생성

다음:
text_unit 기반 읽기 + evidence span 고정
```

---

## 3.3 Discovery Agent 개념이 프로젝트 비전과 잘 맞음

이번 논의에서 나온 Discovery Agent 또는 Associative Explorer는 프로젝트의 핵심 차별점이 될 수 있다.

목표는 사용자가 직접 검색하지 않은 연결까지 발견하는 것이다.

예:

```text
퀘스트 대사를 읽음
→ 이 표현이 책의 창세 신화 구조와 비슷하다고 판단
→ 책 DB로 탐색 방향 전환
→ 유사 문단 발견
→ 성유물/무기 스토리까지 확장
→ 가설 후보 생성
→ 반례 탐색
```

이 기능은 일반적인 검색엔진이나 단순 RAG와 다른 부분이다.

프로젝트 비전의 핵심 문장과도 맞다.

```text
검색은 찾으려는 것을 찾는다.
연구 AI는 찾으려 하지 않았던 연결도 발견해야 한다.
```

---

## 3.4 출처 계층 분리 원칙이 유지됨

이번 논의는 AI의 창의성을 허용하면서도, 공식 근거 없는 단정은 금지한다는 원칙을 유지한다.

최종 답변은 다음 계층을 분리해야 한다.

```text
공식 원문에서 확인되는 내용
공식 텍스트에서 간접적으로 연결되는 내용
AI가 제안하는 가설
반례 또는 약점
현재 신뢰도
```

이 구분은 프로젝트의 신뢰도를 유지하는 핵심이다.

---

## 4. 주의할 점

## 4.1 설계가 너무 빨리 멀티 에이전트화될 위험

이번 논의에는 다음과 같은 agent가 등장한다.

```text
Research Supervisor
Planner Agent
Retrieval Agent
Reader Agent
Discovery Agent
Counter Agent
Hypothesis Agent
Synthesizer Agent
```

최종 구조로는 적절할 수 있다.

하지만 초기 구현부터 실제 독립 agent 여러 개로 나누면 복잡도가 급격히 커진다.

초기 권장 방식:

```text
하나의 research loop
+ planner 함수
+ reader 함수
+ discovery 함수
+ counter 함수
+ synthesizer 함수
```

즉, 처음에는 agent를 프로세스나 서비스 단위로 분리하지 말고 역할 함수로 구현한다.

나중에 병목과 책임 경계가 명확해졌을 때 독립 agent로 분리하는 것이 좋다.

---

## 4.2 Validator는 숫자/이름 검사만으로 부족함

정답형 QA에서 작은 LLM을 말투 변환기로 쓰는 구조는 좋다.

하지만 validator를 단순히 다음 정도로만 만들면 부족하다.

```text
숫자 검사
고유명사 검사
금지 추측 표현 검사
```

작은 LLM은 숫자와 이름을 바꾸지 않아도 다음과 같은 오류를 만들 수 있다.

```text
약한 표현을 단정처럼 바꿈
관계 방향을 뒤집음
원문에 없는 원인-결과를 추가함
부정문을 긍정문처럼 바꿈
요약 과정에서 조건을 누락함
```

따라서 validator는 점진적으로 다음 정보를 다뤄야 한다.

```text
allowed_entities
allowed_numbers
allowed_claims
forbidden_claims
source_fields
required_qualifiers
```

특히 연구형 답변에서는 validator가 최종 결론을 검증하기보다, 각 주장에 evidence span이 붙어 있는지를 확인하는 쪽이 더 현실적이다.

---

## 4.3 Research Memory는 오염 위험이 큼

연구 메모리는 반드시 필요하지만, 잘못 설계하면 시스템 품질을 떨어뜨릴 수 있다.

위험한 상황:

```text
AI가 만든 가설을 다음 조사에서 공식 사실처럼 재사용
사용자 선호를 공식 근거보다 강하게 반영
반박된 가설이 계속 검색 확장에 사용됨
오래된 버전의 텍스트를 최신 근거처럼 사용
```

따라서 메모리는 반드시 계층을 나눠야 한다.

```text
공식 원문
자동 추출 관계
사용자 가설
AI 추론
확인 필요
반박됨
폐기됨
```

메모리는 답변을 대신 생성하는 저장소가 아니라, 다음 탐색에서 참고할 연구 노트여야 한다.

---

## 4.4 Discovery Agent는 novelty와 noise를 동시에 만든다

Discovery Agent는 예상 밖 연결을 찾는 데 유용하지만, 관련 없는 문서까지 끌어올 위험도 있다.

따라서 발견 후보에는 반드시 상태가 필요하다.

```text
candidate
accepted
rejected
needs_review
```

그리고 점수도 단순 relevance만 보면 안 된다.

예:

```text
score = relevance + novelty + source_quality - noise_penalty
```

처음부터 완전 자동 결론을 내리기보다, Discovery Agent는 후보를 만들고 Synthesizer가 신중하게 계층을 나누는 구조가 좋다.

---

## 5. 기존 프로젝트와의 관계

이번 논의는 기존 프로젝트를 갈아엎는 방향이 아니다.

기존 구조 위에 다음 계층을 얹는 방향이다.

현재 프로젝트:

```text
canonical documents / chunks
SQLite FTS
entity alias index
query router
search / investigate
Evidence Pack v0.5
```

이번 논의가 추가하는 계층:

```text
text_units
read_window
expand_window
evidence_spans
similar passage search
motif index
discovery links
hypothesis manager
workspace memory
research loop
```

따라서 문서화할 때도 다음처럼 연결하는 것이 좋다.

```text
현재 검색엔진은 research agent의 검색 도구가 된다.
Evidence Pack은 research report의 근거 묶음이 된다.
chunks는 검색 단위이고, text_units는 읽기 단위가 된다.
LLM은 DB를 직접 읽지 않고 제한된 tool을 통해 읽는다.
```

---

## 6. 권장 문서화 구조

이번 논의를 정리할 때는 다음 순서가 좋다.

```text
1. 현재 엔진의 위치
2. 정답형 QA Engine
3. Source Reader / Reading Window
4. Evidence Span 고정
5. Research Loop
6. Discovery Agent
7. Counter / Hypothesis / Memory
8. Cloudflare / Oracle / Local 배치
9. 단계별 로드맵
10. 구현 리스크
```

이 순서가 좋은 이유는, 비전에서 바로 멀티 에이전트로 뛰지 않고 현재 구현 가능한 기반부터 쌓기 때문이다.

---

## 7. 권장 구현 순서

초기 구현은 다음 순서가 현실적이다.

## 7.1 Phase 1: 읽기 단위 정리

```text
text_units 테이블 정의
document / section / unit_index 정리
read_unit 구현
read_window 구현
expand_window 구현
```

목표:

```text
검색 결과를 원문 읽기 세션으로 확장할 수 있게 만들기.
```

---

## 7.2 Phase 2: Evidence Span 고정

```text
evidence_spans 테이블 정의
pin_evidence 구현
Evidence Pack과 evidence_span 연결
인용 가능한 quote 저장
```

목표:

```text
최종 답변의 모든 핵심 주장을 추적 가능한 원문 span에 연결하기.
```

---

## 7.3 Phase 3: 정답형 QA Engine

```text
intent별 answer schema 정의
basic_lookup 템플릿 구현
summary 템플릿 구현
comparison 템플릿 구현
small LLM rewriter 연결
validator 구현
fallback 구현
```

목표:

```text
쉬운 질문은 빠르고 안정적으로 답변하기.
```

---

## 7.4 Phase 4: Research Loop v1

```text
research plan 생성
검색 tool 호출
read_window 호출
evidence pinning
간단한 counter search
가설별 보고서 생성
```

목표:

```text
멀티 agent가 아니라 단일 research loop로 연구형 답변의 최소 버전 구현.
```

---

## 7.5 Phase 5: Discovery Agent v1

```text
motif seed 작성
find_similar_passages 구현
cross content_type search 구현
discovery_links 저장
candidate / accepted / rejected 상태 관리
```

목표:

```text
사용자가 직접 검색하지 않은 연결 후보를 발견하기.
```

---

## 7.6 Phase 6: Hypothesis / Memory

```text
hypotheses 테이블 정의
research_notes 정의
research_evidence 정의
가설 상태 관리
메모리 출처 계층 분리
```

목표:

```text
한 번의 답변이 아니라 장기 연구 흐름을 이어가기.
```

---

## 8. 최종 판단

이번 논의는 기존 설계를 대체하기보다, 기존 검색엔진을 연구형 에이전트로 확장하는 데 필요한 다음 층을 잘 설명한다.

특히 다음 세 가지는 반드시 문서와 구현 계획에 반영할 가치가 있다.

```text
1. 정답형 QA와 연구형 탐색의 분리
2. Reading Window / Progressive Disclosure
3. Discovery Agent / 능동형 탐색
```

하지만 다음 세 가지는 주의해야 한다.

```text
1. 처음부터 멀티 에이전트 구조로 과설계하지 않기
2. 작은 LLM rewriter의 validator를 과소평가하지 않기
3. Research Memory가 자기 추측을 사실처럼 재사용하지 못하게 하기
```

최종 결론:

```text
이번 논의는 방향이 맞다.
다만 구현은 작게 시작해야 한다.

먼저 원문을 정확히 읽고 확장하는 도구를 만들고,
그다음 evidence span을 고정하고,
그 위에 research loop와 Discovery Agent를 얹는 순서가 가장 안전하다.
```

