# 로드맵

현재 프로젝트는 데이터 수집과 검색엔진 코어, 기본 평가 체계가 구축된 **v0.5** 상태입니다.

## 현재 위치

```text
완료에 가까움:
- Project Amber 수집
- TextMap 수집
- Project Amber 전처리
- canonical 문서/청크 생성
- RAG 자산 생성
- SQLite FTS 검색 DB
- 엔티티/별칭 인덱스
- 개발자용 검색 CLI
- Evidence Pack 초안
- 기본 Query Router
- Evidence Pack v0.5 스키마
- 검색 평가셋
- 평가 리포트 생성

아직 없음:
- 벡터 검색
- 모티프 인덱스
- Translation Diff Index
- Similar Passage Index
- Co-occurrence Index
- Graph Search
- Workspace Memory
- API / 웹 UI
- 실제 LLM 답변 생성
```

## v0.5 조건

v0.5는 검색엔진이 개발자용으로 안정적으로 평가 가능한 상태를 의미합니다.

```text
1. 검색 평가셋 존재
2. 주요 질의의 기대 문서/엔티티 정의
3. search / investigate 결과를 자동 검증
4. 고유명사/개념 사전 보강
5. Evidence Pack 구조 확정
6. 검색 결과 중복률과 노이즈율 확인
7. 기본 Query Router 초안
```

v0.5에서는 아직 웹 UI가 없어도 됩니다.

현재 이 조건은 충족했습니다. v0.5 평가셋 기준 결과:

```text
canonical_recall_at_k: 1.0
concept_recall: 1.0
content_type_recall: 1.0
MRR: 0.9167
route_accuracy: 1.0
```

## v0.6 조건

```text
1. Basic Lookup / Summary / Analysis / Research 모드별 처리 분기
2. Query Router 정확도 개선
3. Exact Lookup 강화
4. Source 조회 구조 정리
5. 모티프 seed 사전 추가
```

## v0.7 조건

```text
1. 벡터 검색 구현
2. FTS + Vector + Entity 하이브리드 검색
3. Reranking 평가
4. LLM 커넥터 연결
5. Evidence Pack 기반 답변 생성
```

## v0.8 조건

```text
1. FastAPI 기반 Search Tool API
2. Source API
3. NDJSON 또는 SSE 스트리밍 API
4. 개발자용 채팅 엔드포인트
```

## v0.9 조건

```text
1. Workspace Memory
2. 여러 가설 상태 관리
3. Memory Patch
4. Memory Event Log
5. 사용자 관점 전환 해석
```

## v1.0 조건

v1.0은 사용자가 실제로 연구 보조 도구로 쓸 수 있는 상태입니다.

```text
1. 공식 DB 재수집/재빌드 가능
2. 검색 평가셋 통과
3. 다국어 고유명사 확장 안정화
4. Evidence Pack 기반 답변 생성
5. 공식 근거와 AI 추론 분리
6. 반례 후보 제시
7. Source Viewer 또는 Source API 제공
8. 워크스페이스별 연구 메모리
9. 재현 가능한 빌드/검증 문서
```

## 우선순위

지금 당장 중요한 것은 웹 UI가 아니라 검색 품질입니다.

```text
1. 검색 평가셋 확대
2. 랭킹 품질 튜닝
3. 모티프 seed
4. 벡터 검색
5. Translation Diff / Similar Passage / Co-occurrence Index
6. API
7. 워크스페이스 메모리
8. 프론트엔드
```

이 순서를 지켜야 LLM을 붙였을 때 그럴듯한 추측만 늘어나는 것이 아니라, 공식 DB를 실제로 탐색하는 연구 AI가 됩니다.
