# Research Agent 추가 논의 정리

## 1. 문서 목적

이 문서는 원신 Lore Research Agent 설계 과정에서 추가로 논의한 내용을 정리한다.

기존 문서들이 프로젝트 비전, 현재 검색엔진, 로드맵, 아키텍처를 설명한다면, 이 문서는 다음 주제를 중심으로 한다.

```text
현재 검색엔진의 위치
정답형 QA Engine
작은 로컬 LLM을 이용한 답변 풍성화
research route의 원문 탐색 방식
Reading Window / Progressive Disclosure
Discovery Agent / 능동형 탐색
Cloudflare / Oracle / Local 역할 분담
구현 순서
```

핵심 결론은 다음이다.

```text
정답형 질문은 엔진이 생각하고 LLM이 말한다.
연구형 질문은 LLM이 탐색하고 엔진이 증거를 검증한다.
```

---

## 2. 현재 검색엔진의 위치

현재 검색엔진은 단순 키워드 검색보다 발전된 구조다.

현재 가능한 일:

```text
고유명사 검색
별칭 검색
다국어 표현 검색
TextMap 보조 검색
공식 텍스트 탐색
퀘스트 / 책 / 캐릭터 자료 우선 랭킹
Evidence Pack 생성
```

현재 흐름:

```text
사용자 질문
→ 질문 라우팅
→ 질의 확장
→ SQLite FTS 기반 하이브리드 검색
→ 랭킹 재계산
→ Evidence Pack 생성
→ 결과 반환
```

예를 들어 `니벨룽겐`을 검색하면 단순히 한국어 문자열만 찾지 않고, 다음 alias를 함께 탐색할 수 있다.

```text
니벨룽겐
Nibelung
ニーベルンゲン
尼伯龙根
```

따라서 현재 엔진은 다음처럼 정의할 수 있다.

```text
준비된 답을 생성하는 엔진이 아니라,
답이 있을 만한 공식 근거를 잘 찾아오는 엔진.
```

다만 아직 다음 기능은 부족하다.

```text
벡터 검색
의미 검색
지식 그래프
모티프 인덱스
공출현 인덱스
진짜 반례 탐지
장기 연구 메모리
복잡한 가설 추론
```

비유하면 다음과 같다.

```text
현재 엔진 = 잘 정리된 거대한 도서관 사서
미래 목표 = 원신 설정 연구원
```

---

## 3. 오프라인 검색으로 가능한 최대 수준

오프라인만으로도 개인용 원신 lore 연구 보조 시스템 수준까지는 구현 가능하다.

가능한 최종 조합:

```text
공식 텍스트 DB
+ 다국어 alias
+ FTS 키워드 검색
+ embedding 의미 검색
+ 엔티티 그래프
+ 공출현 통계
+ claim 추출
+ research memory
+ 로컬 LLM 요약 / 문장화
```

가능한 작업:

```text
공식 텍스트 기반 검색
스토리 요약
성유물 효과 설명
캐릭터 기본 정보 조회
퀘스트 대사 검색
책 내용 검색
언어별 표현 차이 비교
관련 개념 연결
가설별 찬성 / 반대 근거 정리
이전 연구 이어가기
```

한계:

```text
DB 밖 정보는 모른다
새 버전 텍스트는 DB 업데이트 전까지 모른다
은유 / 상징 해석은 약하다
진짜 논리적 반례 탐지는 어렵다
복잡한 가설 추론은 한계가 있다
잘못된 연구 메모리가 누적되면 결과가 오염된다
```

현실적인 최고 목표:

```text
답을 맞히는 AI가 아니라,
연구자가 놓친 근거를 찾아주는 AI.
```

---

## 4. 정답형 QA Engine

정답형 질문은 정답이 DB 안에 있고 답변 구조가 정형화 가능한 질문이다.

예:

```text
절연의 기치 효과 알려줘
푸리나가 누구야?
수메르 마신임무 요약해줘
```

이런 질문은 LLM이 자유롭게 추론할 필요가 없다.

권장 흐름:

```text
User Query
→ Intent Router
→ Entity Resolver
→ Fact Resolver
→ Structured Fact JSON
→ Template Draft Generator
→ Local LLM Rewriter
→ Validator
→ Final Answer
```

핵심 원칙:

```text
정확도 = 로컬 DB / 규칙 / 검색 / 검증
자연스러움 = 작은 로컬 LLM
안전성 = validator
```

예시 facts JSON:

```json
{
  "intent": "artifact_effect_lookup",
  "artifact": "절연의 기치",
  "two_piece": "원소 충전 효율 +20%",
  "four_piece": "원소 충전 효율의 25%만큼 원소폭발 피해가 증가한다.",
  "max_bonus": "최대 75%",
  "confidence": 1.0,
  "source": "local_artifact_db"
}
```

템플릿 draft:

```text
절연의 기치는 성유물 세트입니다.
2세트 효과는 원소 충전 효율 +20%입니다.
4세트 효과는 원소 충전 효율에 비례해 원소폭발 피해를 증가시키며, 최대 75%까지 증가합니다.
```

작은 LLM은 이 draft를 자연스럽게 다듬기만 한다.

---

## 5. 작은 로컬 LLM을 이용한 답변 풍성화

작은 LLM은 사실을 판단하는 뇌가 아니라, 문장화와 답변 풍성화를 담당한다.

허용:

```text
문장 자연스럽게 만들기
반복 줄이기
말투 통일
문단 흐름 개선
관련 facts를 읽기 좋게 묶기
```

금지:

```text
성유물 수치 추측
캐릭터 설정 추가
공식 텍스트에 없는 관계 단정
검색 결과에 없는 떡밥 생성
가설을 사실처럼 말하기
```

권장 모델:

```text
Qwen2.5 1.5B GGUF
TinyLlama 1.1B
SmolLM 1.7B
```

권장 런타임:

```text
llama.cpp
llama-cpp-python
Ollama
```

권장 파라미터:

```text
temperature = 0.15 ~ 0.25
top_p = 0.8 ~ 0.9
max_tokens = 256
```

프롬프트 원칙:

```text
아래 FACTS에 있는 정보만 사용하라.
새로운 사실을 추가하지 마라.
숫자와 이름을 바꾸지 마라.
추측하지 마라.
자연스러운 한국어로만 다듬어라.
```

fallback 구조:

```text
Template Draft
→ LLM Rewrite
→ Validation
→ Pass = LLM output
→ Fail = Original draft
```

즉, 모델이 없거나 검증에 실패해도 시스템은 정상 답변을 낼 수 있어야 한다.

---

## 6. Validator

작은 LLM이 facts에 없는 내용을 추가하지 못하게 검증기가 필요하다.

기본 검증:

```text
숫자 추출
고유명사 추출
효과 수치 비교
금지 추측 표현 검사
```

예:

```python
def validate_answer(answer, facts):
    for number in extract_numbers(answer):
        if number not in facts.allowed_numbers:
            return False

    for name in extract_entities(answer):
        if name not in facts.allowed_entities:
            return False

    return True
```

하지만 숫자와 이름만으로는 부족하다.

추가로 고려할 검증 대상:

```text
allowed_claims
forbidden_claims
source_fields
required_qualifiers
관계 방향
부정 / 긍정 유지
조건 누락 여부
```

정답형 QA에서는 validator가 최종 답변의 안전성을 결정한다.

연구형 모드에서는 validator가 답변 전체의 진위를 판정하기보다, 각 주장에 evidence span이 연결되어 있는지를 확인하는 역할에 가깝다.

---

## 7. 연구형 질문

연구형 질문은 정답이 DB 안에 직접 존재하지 않는 질문이다.

예:

```text
파네스와 천리의 관계 가능성은?
페이몬 정체를 공식 근거 중심으로 다시 봐줘.
세계수 기억 조작이 천리와 연결될 수 있어?
```

이런 질문은 단순 검색으로 처리하면 부족하다.

권장 흐름:

```text
LLM이 탐색 계획을 세움
→ 검색엔진이 공식 원문 후보를 찾음
→ Source Reader가 앞뒤 문맥을 펼침
→ Discovery Agent가 새 연결 후보를 발견함
→ Counter Agent가 반례를 찾음
→ Synthesizer가 가설별 보고서를 작성함
```

핵심 원칙:

```text
검색엔진이 LLM을 제한하는 것이 아니라,
검색엔진이 LLM의 추론을 공식 원문에 접지시킨다.
```

연구형 답변에서는 다음 계층을 분리해야 한다.

```text
공식 원문에서 확인되는 내용
공식 텍스트에서 간접적으로 연결되는 내용
AI가 제안하는 가설
반례 또는 약점
현재 신뢰도
```

---

## 8. LLM의 DB 접근 방식

LLM에게 SQL 직접 접근을 주지 않는다.

대신 제한된 tool을 제공한다.

검색 도구:

```python
search_text(query, filters=None, limit=20)
search_entity(entity_name, langs=None)
search_by_alias(alias)
search_textmap(query, langs=["ko", "en", "ja", "zh"])
```

원문 읽기 도구:

```python
read_unit(unit_id)
read_window(unit_id, before=5, after=5)
expand_window(window_id, direction="after", amount=10)
read_section(section_id)
read_document(document_id)
read_neighbor_document(document_id, direction)
```

문맥 확장 도구:

```python
read_quest_chain(quest_id)
read_book_series(book_series_id)
read_character_story(character_id)
read_artifact_set_story(set_id)
read_weapon_story(weapon_id)
```

다국어 비교 도구:

```python
read_parallel(unit_id, langs=["ko", "en", "ja", "zh"])
find_translation_diff(unit_id)
search_parallel_expression(expression)
```

증거 고정 도구:

```python
pin_evidence(document_id, start_char, end_char, role, source_level, note)
```

이 방식은 LLM의 자유로운 탐색을 허용하면서도, DB 접근을 안전하고 추적 가능하게 만든다.

---

## 9. Reading Window

research route에서는 검색 hit 한 문장만 반환하면 문맥이 끊긴다.

따라서 모든 검색 결과는 Reading Window로 확장 가능해야 한다.

예시 구조:

```json
{
  "window_id": "W-001",
  "document_id": "doc_123",
  "document_title": "수메르 마신임무 3장 5막",
  "section_id": "sec_12",
  "section_title": "세계수 내부",
  "center_unit": "unit_1042",
  "before": ["...", "..."],
  "center": "...",
  "after": ["...", "..."],
  "next_actions": [
    "expand_before",
    "expand_after",
    "read_section",
    "read_document",
    "read_parallel_translation"
  ]
}
```

핵심 기능:

```text
검색된 위치의 앞뒤 문맥 제공
필요할 때 이전 / 이후 문맥 추가 확장
섹션 전체 읽기
문서 전체 읽기
관련 문서 읽기
다국어 병렬 원문 읽기
```

한 줄 요약:

```text
find 도구가 아니라, 읽으면서 확장하는 원문 브라우저가 필요하다.
```

---

## 10. Progressive Disclosure

AI에게 처음부터 문서 전체를 주면 context 낭비가 크다.

대신 필요할 때 단계적으로 펼친다.

```text
검색 결과 1문장
→ 앞뒤 5문장
→ 앞뒤 20문장
→ 섹션 전체
→ 문서 전체
→ 관련 문서
→ 시리즈 전체
```

장점:

```text
context window 절약
문맥 단절 완화
LLM이 스스로 더 읽을 범위 선택 가능
탐색 로그 추적 가능
```

---

## 11. text_units

현재 chunk는 검색 단위로는 유용하지만, 연구형 원문 읽기에는 더 작은 단위가 필요하다.

권장 스키마:

```sql
CREATE TABLE text_units (
    unit_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    section_id TEXT,
    unit_index INTEGER NOT NULL,
    lang TEXT NOT NULL,
    text TEXT NOT NULL,
    start_char INTEGER,
    end_char INTEGER,
    speaker TEXT,
    content_type TEXT,
    metadata_json TEXT
);
```

인덱스:

```sql
CREATE INDEX idx_text_units_doc_index
ON text_units(document_id, unit_index);

CREATE INDEX idx_text_units_section
ON text_units(section_id, unit_index);

CREATE INDEX idx_text_units_lang
ON text_units(lang);
```

정리:

```text
chunks = 검색 단위
text_units = 읽기 단위
evidence_spans = 인용 / 주장 고정 단위
```

---

## 12. Evidence Span

모든 최종 주장은 evidence span에 고정되어야 한다.

권장 스키마:

```sql
CREATE TABLE evidence_spans (
    evidence_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    unit_id TEXT,
    start_char INTEGER,
    end_char INTEGER,
    quote TEXT NOT NULL,
    role TEXT NOT NULL,
    source_level TEXT NOT NULL,
    confidence REAL,
    created_by TEXT,
    created_at TEXT,
    note TEXT
);
```

role 예:

```text
direct_support
indirect_support
background
translation_variant
counter_candidate
weak_signal
motif_parallel
```

목표:

```text
AI의 최종 보고서가 원문 근거와 분리되지 않게 하기.
```

---

## 13. Discovery Agent

Discovery Agent는 능동형 탐색을 담당한다.

목표:

```text
현재 읽은 원문에서 다음에 읽을 가치가 있는 다른 자료를 스스로 찾아내기.
```

예:

```text
퀘스트 대사를 읽음
→ 책에서 본 표현과 비슷하다고 판단
→ 책 DB 탐색
→ 성유물 스토리 탐색
→ 무기 스토리 탐색
→ 유사 구조 발견
→ 가설 후보 생성
```

역할:

```text
현재 읽은 대사 / 문단에서 핵심 표현 추출
고유명사뿐 아니라 상징어 / 모티프 / 구조어 추출
다음에 읽을 자료 유형 결정
책 / 성유물 / 무기 / 캐릭터 / 퀘스트로 탐색 점프
유사 문단과 반복 표현 탐색
연결 후보 저장
```

출력 예:

```json
{
  "trigger_span": "하늘의 왕좌가 뒤집혔다",
  "detected_motifs": ["하늘", "왕좌", "전복", "질서"],
  "next_search_targets": [
    {
      "content_type": "book",
      "query": "왕좌 하늘 질서"
    },
    {
      "content_type": "artifact",
      "query": "왕좌 질서"
    },
    {
      "content_type": "quest",
      "query": "하늘 전복"
    }
  ],
  "reason": "현재 문장에 책/신화적 서술에서 반복될 수 있는 상징 조합이 있음"
}
```

---

## 14. Similar Passage / Motif / Co-occurrence

능동형 탐색을 위해 다음 인덱스가 필요하다.

## 14.1 Similar Passage Index

목표:

```text
표현이 다르더라도 의미 / 상징 / 서사 구조가 비슷한 passage를 찾기.
```

대상:

```text
퀘스트 대사
책 문단
성유물 스토리
무기 스토리
캐릭터 대사
캐릭터 스토리
재료 설명
TextMap
```

구현:

```text
text_unit 단위 embedding 생성
content_type별 vector index 생성
source span과 유사한 passage 검색
```

## 14.2 Motif Index

목표:

```text
고유명사가 아니라 반복 상징 / 구조를 인덱싱한다.
```

예:

```text
왕좌
하늘
창세
금지된 지식
기억 삭제
세계수
심연 침식
용
달
그림자
거짓 하늘
운명
실
베틀
```

## 14.3 Co-occurrence Index

목표:

```text
같이 자주 등장하는 엔티티 / 모티프 조합을 찾는다.
```

예:

```text
파네스 ↔ 네 그림자
천리 ↔ 셀레스티아
니벨룽겐 ↔ 용왕
```

PMI 같은 통계량을 사용하면 단순 빈도가 아니라 특별히 같이 자주 나오는 관계를 찾을 수 있다.

---

## 15. Knowledge Graph

Knowledge Graph는 문서 단위가 아니라 관계 단위로 탐색하기 위한 계층이다.

예:

```text
파네스 - created_candidate -> 네 그림자
천리 - related_to -> 셀레스티아
카리베르트 - connected_to -> 운명의 베틀
```

처음에는 Neo4j 같은 별도 DB보다 SQLite 테이블로 시작하는 것이 현실적이다.

권장 테이블:

```sql
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    entity_type TEXT
);

CREATE TABLE entity_aliases (
    alias TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    lang TEXT,
    PRIMARY KEY (alias, entity_id)
);

CREATE TABLE relations (
    relation_id INTEGER PRIMARY KEY,
    subject_id TEXT NOT NULL,
    predicate TEXT NOT NULL,
    object_id TEXT NOT NULL,
    source_chunk_id TEXT,
    confidence REAL DEFAULT 0.5,
    extraction_method TEXT
);
```

초기 relation type:

```text
same_as
related_to
mentioned_with
opposes_candidate
created_candidate
belongs_to
located_in
descendant_of
```

---

## 16. Counter Agent

연구형 질문에서는 지지 근거만 찾으면 안 된다.

Counter Agent는 반례 후보를 찾는다.

역할:

```text
가설별 약점 찾기
부정 / 대조 표현 검색
시점 충돌 탐색
동일성 가설의 분리 근거 탐색
번역상 약화 표현 탐색
```

예:

```json
{
  "hypothesis_id": "H-001",
  "counter_candidates": [
    {
      "evidence_id": "E-045",
      "type": "timeline_conflict",
      "reason": "두 존재의 활동 시점이 다르게 제시될 가능성"
    }
  ]
}
```

Counter Agent는 최종 판정을 내리는 모듈이 아니라, 반례 후보를 제공하는 모듈이다.

---

## 17. Hypothesis Manager

연구형 답변은 하나의 결론으로 바로 수렴하면 안 된다.

여러 가설을 병렬로 유지해야 한다.

예:

```text
A. 파네스 = 천리 동일 존재설
B. 파네스 체계 → 천리 체계 계승설
C. 같은 질서 계열의 별개 존재설
D. 창조자-관리자 관계설
E. 상징적으로 유사하지만 직접 관계는 약한 관계
```

가설 상태:

```text
active
parallel
weakened
contradicted
rejected
archived
```

중요한 원칙:

```text
사용자의 새 관점은 기존 가설을 즉시 폐기하는 것이 아니라,
병렬 가설 또는 관점 전환 후보로 저장한다.
```

---

## 18. Workspace Memory

연구는 한 번의 답변으로 끝나지 않는다.

저장 대상:

```text
중심 가설
병렬 가설
약화된 가설
반박된 가설
폐기된 가설
사용자 선호
반례 노트
증거 span
연결 후보
탐색 로그
```

메모리 계층:

```text
공식 원문
자동 추출 관계
사용자 가설
AI 추론
확인 필요
반박됨
폐기됨
```

메모리는 답변을 대신 생성하는 저장소가 아니라, 다음 탐색에서 참고할 연구 노트다.

---

## 19. Cloudflare / Oracle / Local 역할 분담

research route의 무거운 작업은 Cloudflare 단독 처리보다 Cloudflare + Oracle / Local 하이브리드가 적합하다.

권장 역할:

```text
Cloudflare:
- API gateway
- job 생성
- 상태 관리
- 캐시
- 가벼운 응답 전달
- Workers AI를 통한 짧은 rewriter

Oracle / Local Server:
- SQLite FTS
- TextMap 검색
- Vector Search
- Graph Search
- Research Agent loop
- Evidence Pack 생성
- Workspace Memory

LLM:
- 탐색 계획
- 가설 생성
- 문맥 해석
- 최종 보고서 작성
```

비유:

```text
Cloudflare = 접수처 / 지휘소
Oracle = 연구실 / 검색 서버
LLM = 연구자 / 보고서 작성자
```

research job 흐름:

```text
/research 요청
→ Cloudflare Worker가 job_id 생성
→ D1 또는 Queue에 job 저장
→ Oracle worker가 job 수신
→ Oracle에서 investigate / research loop 실행
→ Evidence Pack JSON 생성
→ R2 또는 DB에 결과 저장
→ Cloudflare가 결과 반환
```

---

## 20. 구현 순서

전체를 한 번에 구현하지 않는다.

권장 순서:

```text
1. 현재 FTS 검색 안정화
2. answer schema 정의
3. basic_lookup 답변 템플릿 구현
4. story_summary 답변 템플릿 구현
5. comparison 답변 템플릿 구현
6. 작은 LLM rewriter 연결
7. validator 구현
8. text_units / read_window 구현
9. evidence_spans / pin_evidence 구현
10. research loop v1 구현
11. embedding search 추가
12. similar passage search 추가
13. co-occurrence index 추가
14. motif index 추가
15. knowledge graph 추가
16. research memory 추가
17. contradiction candidate finder 추가
18. Discovery Agent 고도화
```

초기 목표:

```text
성유물 효과
캐릭터 기본 정보
퀘스트 요약
스토리 요약
언어별 표현 차이
관련 근거 묶음
```

그다음에 가설 분석으로 확장한다.

---

## 21. 최종 정리

이번 논의의 핵심은 다음이다.

```text
검색엔진은 공식 원문을 정확히 찾는 도구다.
LLM은 탐색 방향을 세우고 가설을 비교하는 연구자다.
Evidence Pack은 근거를 고정하는 자료 묶음이다.
```

최종 시스템은 다음 방향으로 발전한다.

```text
검색엔진
→ 원신 Lore QA Engine
→ 오프라인 연구 보조 시스템
→ 탐색형 연구 에이전트
```

가장 중요한 설계 원칙:

```text
정답형 질문:
엔진이 생각하고 LLM이 말한다.

연구형 질문:
LLM이 탐색하고 엔진이 증거를 검증한다.
```

그리고 최종 목표:

```text
AI가 공식 원문을 읽고,
앞뒤 문맥을 펼치고,
다른 책 / 대사 / 아이템 설명으로 점프하고,
예상 밖 연결을 발견하고,
근거와 반례를 분리해,
여러 가설을 비교하는 연구형 에이전트.
```

