# 현재 논의 정리 및 한계점 문서

> 기준 시점: 2026-06-28  
> 프로젝트: `Genshin-Impact-Story-AI`  
> 목적: 지금까지 논의한 v2 구조, 로컬 LLM 테스트 단계, 질문 가능 범위, 현재 한계, 다음 개발 우선순위를 정리한다.

---

## 1. 핵심 결론

현재 프로젝트는 최종 비전인 **원신 스토리 연구 AI**까지 간 상태는 아니다.

현재 구현 수준은 다음에 가깝다.

```text
공식 데이터 기반 정형 QA 엔진 + v2 Project Amber DB 기반 일부 답변 기능 + 로컬 LLM 리드 문장 보정
```

즉 현재 가능한 핵심 기능은 다음이다.

- 성유물 효과 조회
- 무기 기본정보 조회
- 무기 R1~R5 제련 효과 조회
- 캐릭터 기본정보 조회
- 캐릭터 별자리 조회
- 캐릭터 특성 조회
- 일부 대화형 후속질문
- 직전 답변의 출처 metadata 표시

아직 어려운 기능은 다음이다.

- 스토리 요약
- 퀘스트/책 전체 요약
- 관계 분석
- 떡밥/가설/추측 비교
- 원문 앞뒤 문맥 read window
- 근거 span 고정
- 반례 검색
- Multi-Scout 연구 루프
- 웹 UI / API 서버 / 실제 ChatGPT형 제품 경험

---

## 2. v2는 어디까지 들어갔는가

현재 v2는 **아예 안 들어간 것이 아니다.**

정확히는 다음과 같다.

| 기능 | 현재 기본 사용 DB | 상태 |
|---|---|---|
| `lore_search_engine.py answer` | v2 `data/processed/search_v2/project_amber_search.sqlite3` | 사용 중 |
| `lore_search_engine.py chat` | 내부적으로 answer 사용 → v2 | 사용 중 |
| `lore_chat.py` | 내부적으로 answer/chat 사용 → v2 | 사용 중 |
| `search_lore.py --db-version v2` | v2 | 수동 확인 가능 |
| `lore_search_engine.py search` | v1 `data/processed/search/lore_search.sqlite3` | 아직 v1 |
| `lore_search_engine.py investigate` | v1 `data/processed/search/lore_search.sqlite3` | 아직 v1 |
| `search_lore.py` 기본값 | v1 | 아직 v1 |

따라서 현재 상태를 한 문장으로 말하면 다음과 같다.

```text
v2는 정답형 QA에는 들어갔지만, 메인 search/investigate 경로에는 아직 승격되지 않은 과도기 상태다.
```

---

## 3. v2 작업은 삽질인가?

아니다.

v2는 다음 단계의 기반 공사다.

v2가 만든 핵심 자산은 다음이다.

- Project Amber 중심 corpus 재정리
- readable v2 산출물
- canonical/project_amber_v2 산출물
- search_v2 SQLite DB
- documents / sections / text_units 구조
- text_units FTS 검색 기반
- TextMap 보조 검색 테이블
- 캐릭터/무기/성유물 정형 QA의 RAW 기반 facts 추출
- Source Reader, Evidence Span, Summary Index, Research Loop로 확장할 수 있는 구조

비유하면 다음과 같다.

```text
v2 = 새 고속도로를 깔아둔 상태
answer/chat = 이미 새 고속도로를 일부 사용 중
search/investigate = 아직 옛 도로를 기본으로 사용 중
```

문제는 v2를 만든 것이 아니라, **v2를 메인 검색 경로로 아직 승격하지 않은 것**이다.

---

## 4. 현재 성능 손실이 발생하는 부분

정형 QA에서는 v2가 이미 적용되어 있으므로 성능 손실이 크지 않다.

예를 들어 다음 질문들은 v2의 효과를 이미 받는다.

```text
푸리나 기본정보
푸리나 별자리
푸리나 특성
안개를 가르는 회광 정보
안개를 가르는 회광 R1부터 R5까지 보여줘
절연의 기치 효과
```

반면 조사형/연구형 흐름에서는 손실이 크다.

예를 들어 다음 질문은 아직 v2 메인 검색엔진의 이점을 충분히 쓰지 못한다.

```text
천리 관련 공식 텍스트 찾아줘
니벨룽겐 언급 찾아줘
페이몬 정체 근거 조사해줘
세계수와 기억 조작 관련 대사 찾아줘
파네스와 천리 관계 분석해줘
```

손실이 생기는 이유는 다음이다.

- `search/investigate`가 아직 v1 DB를 기본으로 사용한다.
- v2의 `text_units` 기반 검색이 메인 엔진에 통합되지 않았다.
- Source Reader가 아직 v2 text unit을 읽지 못한다.
- Evidence Span이 아직 없다.
- Summary/Analysis/Research route가 실제 답변 생성까지 이어지지 않는다.

---

## 5. 현재 질문 가능 수준

현재 질문 가능 수준은 다음과 같이 나눌 수 있다.

| 질문 유형 | 가능도 | 예시 |
|---|---:|---|
| 성유물 효과 조회 | 높음 | `절연의 기치 효과` |
| 무기 기본정보 | 높음 | `안개를 가르는 회광 정보` |
| 무기 R1~R5 | 높음 | `회광 R1부터 R5까지` |
| 캐릭터 기본정보 | 높음 | `푸리나 기본정보` |
| 캐릭터 별자리 | 중상 | `푸리나 별자리` |
| 캐릭터 특성 | 중상 | `푸리나 특성` |
| 짧게/표로/목록으로 | 중상 | `표로 정리` |
| 대화형 후속질문 | 중간 | `별자리도`, `근거는?` |
| 출처 metadata | 중간 | `근거는?` |
| 원문 본문 인용 | 낮음 | Source Reader 미완성 |
| 책/퀘스트 검색 | 중간 | v2 검색 CLI로 가능 |
| 책/퀘스트 요약 | 낮음 | summary route 미구현 |
| 관계 분석 | 낮음 | route만 가능, 답변 미구현 |
| 연구형 추측 | 매우 낮음 | 최종 비전 단계 |
| 공략/추천/티어 | 불가 | 의도적으로 차단 |

---

## 6. 현재 LLM이 하는 일

현재 로컬 LLM은 핵심 추론 엔진이 아니다.

현재 LLM의 역할은 크게 두 가지다.

### 6.1 답변 리드 문장 생성

현재 LLM은 정답형 QA의 본문을 자유롭게 다시 쓰지 않는다.

실제 구조는 다음에 가깝다.

```text
facts 추출
→ deterministic template draft 생성
→ LLM이 draft 앞에 붙일 짧은 리드 문장만 생성
→ validator 통과 시 lead + draft 사용
→ 실패 시 template draft로 fallback
```

즉 LLM은 사실 생성기가 아니라 **표현 보정기**에 가깝다.

이 방식은 보수적이지만 안전하다.

### 6.2 Semantic Parser 초안

질문을 JSON으로 분류하는 semantic parser는 존재한다.

그러나 현재는 다음 수준에 가깝다.

```text
route 후보 분류
intent 후보 분류
entities 표면 문자열 추출
requested_style 추정
```

아직 다음 구조는 아니다.

```text
질문 의미 분석
→ Query Frame 생성
→ 검색 계획 수립
→ Source Reader 호출
→ 근거 pinning
→ 반례 검색
→ 가설/해석/사실 분리
→ 답변 생성
```

따라서 현재는 **LLM 질문 분석 기능이 코드에 일부 들어가 있지만, 메인 사고 구조는 아직 규칙 기반 + exact lookup 중심**이라고 보는 것이 정확하다.

---

## 7. 현재 오해하기 쉬운 부분 정리

### 오해 1. “v2가 아직 안 들어간 것 아닌가?”

아니다.

`answer/chat`에는 v2가 들어가 있다.

다만 `search/investigate`가 아직 v1 기본값이다.

### 오해 2. “v2 만든 게 삽질인가?”

아니다.

v2는 Source Reader, Evidence Span, Summary Index, Research Loop로 가기 위한 기반이다.

문제는 v2를 만든 것이 아니라, 아직 v2가 메인 검색 경로로 승격되지 않은 것이다.

### 오해 3. “LLM이 질문을 분석하고 있는가?”

일부만 그렇다.

semantic parser는 있지만, 아직 Query Frame / Planner / Tool-calling Agent 구조는 아니다.

### 오해 4. “Source Reader가 있는가?”

이름은 있지만 아직 진짜 Source Reader는 아니다.

현재는 직전 답변의 source metadata를 보여주는 수준이다.

진짜 Source Reader는 다음 기능을 포함해야 한다.

- `read_unit(unit_id)`
- `read_window(unit_id, before, after)`
- `read_section(section_id)`
- `read_document(document_id)`
- `read_parallel(canonical_id, languages)`

---

## 8. 현재 한계점

### 8.1 v1/v2 경계 혼재

현재 가장 큰 구조적 한계는 v1과 v2가 섞여 있다는 것이다.

- answer는 v2
- search/investigate는 v1
- search_lore.py는 기본 v1, 옵션 v2

이 상태가 길어지면 다음 문제가 생긴다.

- 디버깅 시 어떤 DB를 보고 있는지 헷갈린다.
- 평가 결과가 실제 v2 품질을 반영하지 못할 수 있다.
- Source Reader 구현 시 v1 chunks와 v2 text_units가 충돌한다.
- README와 실제 동작이 어긋나기 쉽다.

### 8.2 summary/analysis/research route 미구현

라우팅은 존재하지만 실제 답변 생성은 없다.

따라서 다음 질문은 아직 제대로 처리할 수 없다.

```text
수메르 마신임무 요약해줘
푸리나 스토리 요약해줘
파네스와 천리 관계 분석해줘
페이몬 정체 추측해줘
세계수와 기억 조작 연결 가능성 검토해줘
```

### 8.3 Source Reader 미완성

현재는 source metadata만 보여준다.

아직 원문 본문을 앞뒤 문맥과 함께 읽는 기능이 없다.

### 8.4 Evidence Span 미구현

현재 Evidence Pack은 excerpt 중심이다.

최종적으로는 다음 단위가 필요하다.

```text
evidence_id
document_id
section_id
unit_id
quote
start_char
end_char
support_type
source_level
claim_id
```

### 8.5 LLM 질문 분석이 주도권을 갖지 않음

현재는 규칙 기반 라우터와 exact lookup이 중심이다.

LLM semantic parser는 아직 보조적이다.

### 8.6 평가셋이 basic_lookup 중심

현재 평가셋은 정형 QA에는 적합하지만, 다음을 평가하지 못한다.

- summary 품질
- analysis 품질
- research 품질
- source reader 정확도
- evidence span 정확도
- 반례 검색 품질
- translation diff 품질

---

## 9. 로컬 LLM 테스트 단계

아직 v2 승격 전 기준 테스트 절차는 다음과 같다.

```text
1. v2 DB 존재 확인
2. v2 DB 빌드
3. search_lore.py --db-version v2 로 v2 단독 검색 확인
4. answer --no-llm 으로 deterministic QA 확인
5. Ollama/Qwen3 설치 및 실행
6. answer with LLM 확인
7. chat 터미널 확인
8. pytest 실행
9. eval_answer_engine.py 실행
```

권장 테스트 명령은 다음이다.

```powershell
python scripts/build_project_amber_v2.py

python scripts/search_lore.py --db-version v2 "푸리나" --language ko --content-type avatar --limit 5
python scripts/search_lore.py --db-version v2 "안개를 가르는 회광" --language ko --content-type weapon --limit 5
python scripts/search_lore.py --db-version v2 "절연의 기치" --language ko --content-type reliquary --limit 5

python scripts/lore_search_engine.py answer "푸리나 기본정보" --no-llm --text
python scripts/lore_search_engine.py answer "절연의 기치 효과 알려줘" --no-llm --text
python scripts/lore_search_engine.py answer "안개를 가르는 회광 정보" --no-llm --text

python scripts/setup_local_llm.py --install --model qwen3:4b-instruct

python scripts/lore_search_engine.py answer "푸리나 기본정보" --text
python scripts/lore_search_engine.py answer "절연의 기치 효과 알려줘" --text
python scripts/lore_search_engine.py chat --once "안개를 가르는 회광 R1부터 R5까지 보여줘"

pytest tests/test_local_llm.py
pytest tests/test_qa.py

python scripts/eval_answer_engine.py --fail-under
python scripts/eval_answer_engine.py --llm --fail-under
```

판정 기준은 다음이다.

```text
no-LLM answer가 실패한다 = v2 DB / raw_ref / facts extractor 문제
no-LLM은 되는데 LLM만 실패한다 = Ollama / Qwen3 문제
LLM은 되지만 이상한 답변이 나온다 = rewrite / validator 문제
search_lore --db-version v2는 되는데 lore_search_engine.py search 결과가 다르다 = 아직 search가 v1이라 정상
```

---

## 10. 다음 개발 우선순위

### P0. v2 승격 전 정리

- 현재 상태 문서화
- v1/v2 경계 명시
- README에서 v1/v2 사용 명령어 구분
- 버전 체계 정리

### P1. v2를 메인 검색 경로로 승격

- `search_lore.py` 기본값을 v2로 변경
- `lore_search_engine.py search/investigate`에 `--db-version` 추가
- 기본값을 v2로 변경
- v1은 `--db-version v1` 또는 `--legacy`로 유지

주의:

기존 `LoreSearchEngine`을 v2 DB에 바로 물리면 안 된다.

v1은 `chunks` 스키마 기반이고, v2는 `text_units` 스키마 기반이므로 별도 v2 search wrapper가 필요하다.

권장 구조:

```text
src/genshin_lore_db/search_engine/v2_engine.py
  ProjectAmberV2SearchEngine
  search()
  investigate()
  read_unit()
  read_window()
```

### P2. Source Reader 구현

최소 기능:

```text
read_unit(unit_id)
read_window(unit_id, before=5, after=5)
read_document(document_id)
```

목표:

- 검색 결과 클릭 시 원문 확인
- answer 근거 확인 시 실제 본문 재인용
- summary/analysis route의 기반 마련

### P3. Evidence Span 구현

최소 테이블/JSON 구조:

```text
evidence_id
document_id
section_id
unit_id
quote
support_type
source_level
claim_id
```

목표:

- LLM 답변의 각 주장과 원문 근거 연결
- summary/analysis/research validator 기반 마련

### P4. Summary route 구현

처음부터 완벽한 요약 AI를 만들 필요는 없다.

최소 목표:

```text
검색된 문서/section/text_units를 Source Reader로 읽음
→ 핵심 문단 추출
→ 요약 draft 생성
→ 출처 표시
→ unsupported 대신 최소 요약 반환
```

### P5. Analysis route 구현

최소 목표:

```text
공식 사실
해석 가능성
불확실한 부분
추가 확인 필요
```

을 분리해서 답변한다.

### P6. Research route 구현

최종 목표에 가까운 단계다.

처음에는 multi-agent가 아니라 단일 research loop로 시작한다.

```text
Query Frame
→ seed search
→ read window
→ evidence pin
→ expansion
→ counter search
→ hypothesis draft
→ validation
```

---

## 11. 권장 작업 순서 요약

가장 현실적인 다음 순서는 다음이다.

```text
1. 현재 상태 문서화
2. v1/v2 경계 README에 명시
3. v2 검색 wrapper 만들기
4. search/investigate 기본값 v2로 승격
5. Source Reader read_unit/read_window 구현
6. Evidence Span 구현
7. summary route 최소 구현
8. analysis route 최소 구현
9. research loop v1 구현
```

---

## 12. 최종 요약

현재 프로젝트는 다음 단계에 있다.

```text
검색/정형 QA 기반은 꽤 진행됨
v2는 answer/chat에 일부 적용됨
search/investigate는 아직 v1이라 승격 필요
LLM은 아직 질문 분석/연구 주도 엔진이 아니라 보조 역할
Source Reader와 Evidence Span은 다음 핵심 과제
```

따라서 지금의 핵심 판단은 다음이다.

```text
v2는 삽질이 아니다.
다만 v2를 메인 검색 경로로 승격하지 않으면 가치가 잠겨 있다.
다음 개발은 v2 승격 + Source Reader 구현이 맞다.
```

---

# 추가 관찰: 현재 휴리스틱 라우팅의 실제 실패 사례

## 1. 테스트 로그 요약

터미널 상태:

```text
Genshin Lore QA terminal
LLM: on | routing: on | model: qwen3:4b-instruct
```

그러나 실제 동작을 보면 `LLM: on`은 질문 이해/라우팅을 LLM이 주도한다는 의미가 아니다. 현재 LLM은 주로 정답형 QA의 짧은 리드 문장 생성 또는 제한적인 보조 분석에 쓰이며, 핵심 라우팅과 대상 결정은 여전히 휴리스틱/규칙 기반에 가깝다.

대표 로그:

```text
질문> 성유물에 대해서 알려줘
[route=basic_lookup:0.88 | intent=reliquary_effect_lookup | llm=used]
→ 특정 성유물 이름을 묻지 않았는데 "얼음바람 속에서 길잃은 용사"를 답변함.

질문> 아야카의 돌파효과에 대해서 알려줘
[route=basic_lookup:0.88 | intent=reliquary_effect_lookup | llm=used]
→ 아야카를 묻고 있는데 성유물 "얼음바람 속에서 길잃은 용사" 답변으로 잘못 빠짐.

질문> 아야카에 대해서 알려줘
[route=basic_lookup:0.88 | intent=character_basic_info | llm=used]
→ 정상적으로 카미사토 아야카 기본정보를 답변함.

질문> 별자리
[route=basic_lookup:0.88 | intent=reliquary_effect_lookup | llm=used]
→ 직전 대화의 아야카를 이어받지 못하고 성유물 "뇌명을 모시는 자"로 잘못 빠짐.

질문> 아야카 별자리
[route=basic_lookup:0.88 | intent=character_constellation | llm=used]
→ 정상적으로 아야카 별자리 답변.

질문> 아야카 돌파
[route=basic_lookup:0.88 | intent=character_basic_info | llm=used]
→ 아야카 기본정보로 처리됨. 돌파 보너스는 나오지만 사용자가 기대한 '돌파 효과/별자리/돌파 특성'과는 다를 수 있음.
```

## 2. 핵심 문제

현재 문제는 단순히 "LLM이 약하다"가 아니다. 더 정확한 문제는 다음과 같다.

```text
1. 질문에 명시적 엔티티가 없을 때 임의의 첫 검색 결과를 답변한다.
2. 엔티티 타입이 확정되기 전에 intent가 먼저 결정되어 엉뚱한 content_type으로 빠진다.
3. 직전 대화의 entity/context를 follow-up 질문에 충분히 반영하지 못한다.
4. '돌파', '돌파효과', '별자리', '운명의 자리', '특성' 같은 게임 용어가 모호하게 처리된다.
5. LLM routing:on처럼 보이지만 실제 핵심 판단은 휴리스틱 기반이다.
```

## 3. 실패 유형별 해석

### A. Generic query를 구체 항목으로 오답 처리

```text
성유물에 대해서 알려줘
```

이 질문은 특정 성유물 세트 이름이 없다. 따라서 현재 엔진이 특정 성유물 하나를 골라 답변하면 안 된다.

권장 동작:

```text
성유물 세트 이름을 함께 입력해 주세요.
예: 절연의 기치 효과, 청록색 그림자 효과, 얼음바람 속에서 길잃은 용사 효과
```

### B. 엔티티 타입 무시

```text
아야카의 돌파효과에 대해서 알려줘
```

"아야카"는 캐릭터 엔티티다. 따라서 한 번 캐릭터로 resolved 되면 성유물 답변으로 빠지면 안 된다.

권장 처리:

```text
아야카 → avatar 확정
돌파효과 → character_constellation 또는 character_ascension/talent 계열 후보
reliquary_effect_lookup 후보는 제거
```

### C. 후속 질문 context 실패

```text
아야카에 대해서 알려줘
별자리
```

두 번째 질문은 직전 엔티티인 아야카를 이어받아야 한다.

권장 query rewrite:

```text
별자리
→ 아야카 별자리
```

### D. 용어 모호성

```text
아야카 돌파
아야카 돌파효과
```

이 표현은 사용자가 다음 중 무엇을 의미하는지 불명확할 수 있다.

```text
1. 운명의 자리 C1~C6
2. 캐릭터 돌파 보너스 스탯
3. 돌파 재료
4. 돌파 단계별 해금 특성
```

현재 지원 범위가 제한되어 있다면 명확히 안내해야 한다.

권장 응답:

```text
'돌파'는 여러 의미로 쓰일 수 있습니다.
현재는 기본정보의 돌파 보너스와 별자리 정보를 지원합니다.
원하는 항목을 골라 주세요: 기본정보 / 별자리 / 특성
```

## 4. 현재 상태 재정의

기존 문서의 "현재 가능한 질문 수준"은 다음처럼 보강해야 한다.

```text
공식 DB 정형 조회는 가능하다.
그러나 자연어 질문 이해는 아직 안정적이지 않다.
특히 엔티티 생략, 후속 질문, 모호한 게임 용어, generic category query에서 오답 가능성이 높다.
```

더 정확한 현재 수준:

```text
- 특정 이름 + 특정 정보 유형이 명시된 질문: 비교적 안정적
  예: 아야카 별자리, 절연의 기치 효과, 회광 R1~R5

- 특정 이름은 있지만 정보 유형이 모호한 질문: 중간
  예: 아야카 돌파, 푸리나 효과

- 정보 유형만 있고 이름이 없는 질문: 취약
  예: 성유물에 대해서 알려줘, 별자리

- 직전 문맥에 의존하는 후속 질문: 취약
  예: 별자리, 특성도, 근거는?

- 스토리/관계/추측형 질문: 아직 미구현 또는 매우 제한적
```

## 5. 우선 수정해야 할 규칙

### P0. 엔티티 없음 → 답변 금지

`basic_lookup`에서 content_type이 필요한 질문인데 명확한 엔티티가 없으면, 검색 결과 첫 항목을 답변하지 말고 clarification/unsupported로 보내야 한다.

예:

```text
성유물에 대해서 알려줘
무기에 대해서 알려줘
캐릭터 알려줘
```

권장 결과:

```text
구체적인 이름을 입력해 주세요.
```

### P0. entity type lock

엔티티가 `avatar`로 확정되면 성유물/무기 intent로 빠지지 않게 해야 한다.

예:

```text
아야카의 돌파효과
→ entity: 카미사토 아야카
→ content_type: avatar
→ reliquary_effect_lookup 금지
```

### P0. follow-up rewrite

직전 대화에 entity가 있고, 현재 질문이 짧은 intent-only 질문이면 query를 보강한다.

예:

```text
별자리 → 아야카 별자리
특성도 → 아야카 특성
근거는? → 직전 답변 source metadata 또는 source_reader
```

### P1. intent 우선순위 수정

캐릭터 이름이 감지된 상태에서 다음 키워드는 캐릭터 쪽으로 우선 처리한다.

```text
별자리 / 운명의 자리 / C1 / C2 / 1돌 / 2돌 → character_constellation
특성 / 스킬 / 원소전투 / 원소폭발 / 패시브 → character_talent
돌파 / 돌파 보너스 → character_basic_info 또는 character_ascension
```

### P1. ambiguous term handling

`돌파효과`는 바로 임의 답변하지 말고 후보를 나눠야 한다.

```text
아야카 돌파효과
→ "별자리 효과를 말하는 건가요, 돌파 보너스를 말하는 건가요?"
```

단, 개발 초기에는 clarification 대신 기본 우선순위를 정해도 된다.

권장 기본값:

```text
돌파효과 = character_constellation
돌파 보너스 = character_basic_info
돌파 재료 = unsupported 또는 future character_ascension_materials
```

## 6. LLM 질문 분석 도입 시 목표

현재 필요한 것은 단순한 LLM 답변 생성이 아니라 Query Understanding 단계다.

목표 구조:

```text
User Query
→ Conversation Context Merge
→ LLM Semantic Parse / Query Frame
→ Entity Resolver
→ Entity Type Lock
→ Intent Resolver
→ Route Decision
→ Tool Plan
→ Retrieval / QA
→ Validator
→ Answer
```

예시 Query Frame:

```json
{
  "route": "basic_lookup",
  "intent": "character_constellation",
  "entities": [
    {
      "surface": "아야카",
      "canonical_name": "카미사토 아야카",
      "content_type": "avatar"
    }
  ],
  "requires_context": false,
  "ambiguity": null
}
```

후속 질문 예시:

```json
{
  "original_query": "별자리",
  "rewritten_query": "아야카 별자리",
  "route": "basic_lookup",
  "intent": "character_constellation",
  "entities": [
    {
      "canonical_name": "카미사토 아야카",
      "content_type": "avatar",
      "source": "conversation_context"
    }
  ]
}
```

## 7. 결론

이번 테스트 로그는 현재 엔진의 한계를 명확히 보여준다.

```text
v2 DB와 정형 QA 기반은 의미 있다.
하지만 질문 이해 계층은 아직 부족하다.
현재 오답의 핵심 원인은 데이터 부족이 아니라 라우팅/엔티티/문맥 병합 문제다.
따라서 다음 단계는 단순히 LLM 답변 품질을 높이는 것이 아니라,
Query Understanding + Entity Type Lock + Follow-up Rewrite를 먼저 구현하는 것이다.
```


