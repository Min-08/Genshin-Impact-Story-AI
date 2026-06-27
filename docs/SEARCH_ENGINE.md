# 검색엔진

현재 검색엔진은 웹 UI가 아니라 개발자용 코어입니다. 목표는 사용자의 자연어 질문을 공식 텍스트 탐색용 질의로 확장하고, 결과를 Evidence Pack으로 묶어 LLM 또는 사람이 검토할 수 있게 만드는 것입니다.

현재 검색엔진 버전은 **v0.5**이고, Evidence Pack 스키마는 `evidence_pack.v0.5`입니다.

## CLI

```powershell
python scripts/lore_search_engine.py route "세계수와 기억 조작 연결 가능성"
python scripts/lore_search_engine.py search "천리" --limit 5
python scripts/lore_search_engine.py search "Khaenri'ah" --limit 5
python scripts/lore_search_engine.py investigate "페이몬의 정체와 천리 관련 근거" --limit 12
python scripts/eval_search_engine.py
```

`search`는 검색 결과를 그대로 보여주고, `investigate`는 연구용 Evidence Pack과 LLM 프롬프트 패키지 생성을 목표로 합니다.

## 현재 검색 채널

```text
fts_unicode
fts_trigram
title_like
canonical
entity_alias
textmap_optional
vector:none
```

벡터 검색은 아직 실제 구현되지 않았고, 인터페이스만 준비된 상태입니다.

## 질의 확장

검색엔진은 입력된 질문을 그대로 검색하지 않고, 엔티티 별칭과 수동 개념 사전을 통해 확장합니다.

예를 들어 `천리`는 다음 표현으로 확장됩니다.

```text
천리
천리의 주관자
Heavenly Principles
Sustainer of Heavenly Principles
天理
天理の調停者
天理的维系者
```

`Khaenri'ah`처럼 한국어 질문과 직접 매칭되지 않는 표현도 TextMap 병렬 항목을 이용해 `켄리아`, `カーンルイア` 같은 표현으로 확장할 수 있습니다.

## 수동 개념 seed

자동 추출만으로는 원신 핵심 개념을 안정적으로 묶기 어렵기 때문에 수동 seed를 둡니다.

현재 예시:

```text
천리 / 천리의 주관자
켄리아
심연 / 심연 교단
셀레스티아
파네스
세계수
강림자
네 그림자
금지된 지식
운명의 베틀
니벨룽겐
```

이 계층은 앞으로 모티프 seed 사전으로 확장될 예정입니다.

## Ranking

검색 결과는 단순 FTS 점수만으로 정렬하지 않습니다.

```text
검색 채널 점수
언어 가중치
카테고리 가중치
content_type 가중치
중복 문서 상태
seed concept coverage
```

스토리 연구에서는 퀘스트, 서적, 캐릭터 대사, 아이템 설명 등 문서 타입의 중요도가 다르기 때문에 content_type 가중치를 사용합니다.

## Evidence Pack

`investigate` 모드는 검색 결과를 다음 관점으로 묶습니다.

```text
직접 언급
확장 개념 근거
배경 자료
언어별 표현 차이
TextMap 보조
반박 가능성 후보
```

목표는 LLM이 검색 결과를 직접 해석하기 전에, 출처와 근거 유형을 분리한 자료 묶음을 제공하는 것입니다.

v0.5 Evidence Pack은 다음 최상위 필드를 가집니다.

```text
schema_version
query
mode
route
entities
sources
groups
coverage
quality
limitations
```

스키마 파일은 `schemas/evidence_pack.schema.json`에 있습니다.

## 검색 평가

v0.5부터 검색 품질은 `config/search_evaluation_set.json`으로 측정합니다.

```powershell
python scripts/eval_search_engine.py
```

현재 평가 지표:

```text
canonical_recall_at_k
concept_recall
content_type_recall
MRR
route_accuracy
duplicate_status_rate
canonical_repeat_rate
low_signal_rate
```

## 현재 한계

```text
벡터 검색 없음
Query Router는 기본 휴리스틱만 있음
모티프 인덱스 없음
번역 차이 자동 탐지 없음
유사 문장 검색 없음
동시 등장 인덱스 없음
관계 그래프 없음
반례 검색은 아직 후보 그룹 수준
실제 LLM API 호출 없음
```

따라서 현재 검색엔진은 `오프라인 검색 MVP + 하이브리드 검색 초안`으로 보는 것이 맞습니다.

## 다음 강화 방향

1. 검색 평가셋 확대
2. 운명의 베틀처럼 일반 단어가 섞인 질의의 랭킹 개선
3. 모티프 seed 사전 작성
4. 벡터 검색 추가
5. Translation Diff / Similar Passage / Co-occurrence Index 구축
