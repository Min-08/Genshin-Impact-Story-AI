# DB Expansion and Research Data Vision

## 1. 문서 목적

이 문서는 Genshin Impact Story AI에서 현재 Project Amber 기반 DB만으로는 부족한 부분을 정리하고, 앞으로 어떤 데이터를 추가해야 하는지, 그리고 `research` 라우트에서 DB를 어떤 방식으로 사용해야 하는지를 정의한다.

핵심 결론은 다음과 같다.

```text
Project Amber = 공식 게임 텍스트 DB의 핵심 기반
Official Web / YouTube / Map = 공식 세계관 문맥 확장
External Comparative Frame = 연구용 해석 렌즈
Community / Guide Data = 후순위 보조 자료
Research DB = 정답지가 아니라 세계관 구조를 관찰하는 자료
```

---

## 2. 현재 DB의 위치

현재 DB는 주로 Project Amber를 스크래핑한 데이터에 기반한다.

Project Amber 기반 DB는 다음에 강하다.

```text
캐릭터
무기
성유물
아이템
책
텍스트맵
게임 내부 공식 문구
일부 스토리/대사 계열 텍스트
```

이 데이터는 `basic_lookup`과 공식 텍스트 검색의 기반으로 매우 중요하다.

예시:

```text
푸리나의 원소는 무엇인가?
안개를 가르는 회광의 효과는 무엇인가?
절연의 기치 4세트 효과는 무엇인가?
특정 책/텍스트맵에 어떤 문장이 있는가?
```

이런 질문에서는 DB가 사실상 정답지 역할을 한다.

하지만 최종 목표인 대화형 원신 스토리 연구 AI를 만들려면 Project Amber만으로는 부족하다. 원신의 세계관은 게임 내부 텍스트뿐 아니라 공식 영상, 공식 웹 문서, 공식 맵, 이벤트 페이지, PV, 방송, 공간 배치, 외부 신화/종교/철학 구조와의 비교를 통해 더 깊게 해석될 수 있기 때문이다.

---

## 3. 라우트별 DB의 역할

DB는 모든 라우트에서 같은 역할을 하지 않는다.

### 3.1 basic_lookup

```text
DB = 정답지
```

공식 데이터에 있는 값을 그대로 조회한다.

예시:

```text
캐릭터 기본정보
무기 효과
성유물 효과
아이템 설명
책 원문
```

이 라우트에서는 LLM의 창의성이 거의 필요 없다. DB와 규칙이 정답을 결정하고, LLM은 문장만 다듬는다.

---

### 3.2 summary

```text
DB = 요약할 원문
```

특정 캐릭터 스토리, 문서, 임무, 개념을 요약한다.

예시:

```text
푸리나 캐릭터 스토리 요약
세계수와 기억 조작 요약
운명의 베틀 개념 정리
```

이 라우트에서는 Source Reader가 원문 구간을 읽고, LLM이 그 범위 안에서 요약한다.

---

### 3.3 analysis

```text
DB = 해석의 근거
```

여러 공식 근거를 바탕으로 의미를 해석한다.

예시:

```text
세계수 기억 조작이 스토리에 주는 의미
푸리나가 폰타인 서사에서 중요한 이유
셀레스티아와 천리의 관계 해석
```

이 라우트에서는 공식 사실과 해석을 분리해야 한다.

---

### 3.4 research

```text
DB = 세계관 구조를 관찰하기 위한 자료
```

research 모드에서 DB는 정답지가 아니다. DB는 원신 세계관의 반복 구조, 모티프, 상징, 관계, 결핍, 모순, 번역 차이, 공간 배치, 공식 미디어 표현을 관찰하기 위한 자료가 된다.

예시:

```text
파네스와 천리가 같은 존재일 가능성
강림자와 세계수 기억 조작의 관계
천리, 셀레스티아, 파네스, 네 그림자를 연결한 결말 추측
원신 구조와 영지주의/종교/신화적 모티프의 관계
```

research의 목표는 하나의 확정 답을 내는 것이 아니다.

research의 목표는 다음에 가깝다.

```text
공식 자료에서 구조를 추출하고
여러 해석 모델을 만들고
각 모델의 근거와 약점을 비교하고
흥미로운 창의적 가설을 제시하되
공식 사실과 추측의 경계를 유지하는 것
```

---

## 4. 추가로 필요한 DB 영역

## 4.1 Official Web DB

공식 웹 문서는 게임 내부 텍스트와는 다른 표현과 맥락을 제공한다.

수집 대상 후보:

```text
공식 캐릭터 소개 페이지
공식 뉴스/공지
버전 업데이트 페이지
이벤트 페이지
공식 만화
특별 방송 공지/요약
공식 세계관 소개 페이지
```

필요한 이유:

```text
게임 내부 텍스트에는 없는 공식 소개 문구 확보
버전별 공개 순서와 마케팅 문맥 확보
캐릭터/지역/이벤트의 공식 설명 차이 비교
게임 텍스트와 공식 웹 문구의 wording diff 분석
```

Canonical 예시:

```json
{
  "source": "official_web",
  "source_level": "L0_OFFICIAL",
  "url": "...",
  "title": "...",
  "published_at": "...",
  "content_type": "official_article",
  "language": "ko",
  "text": "...",
  "related_entities": ["푸리나", "폰타인"]
}
```

---

## 4.2 Official YouTube / Media DB

원신은 공식 영상에서 스토리, 상징, 캐릭터 해석, 떡밥을 많이 제공한다. 따라서 공식 YouTube와 영상 자료는 research와 analysis에서 매우 중요하다.

수집 대상 후보:

```text
버전 PV
캐릭터 PV
캐릭터 플레이
데인 여담
스토리 PV
세계관 PV
특별 방송
공식 애니메이션 / 단편
공식 채널 설명문
```

저장 대상:

```text
영상 ID
제목
게시일
설명문
자막/스크립트
타임스탬프
언어
관련 캐릭터/지역/개념
원본 URL
```

Canonical 예시:

```json
{
  "source": "official_youtube",
  "source_level": "L0_OFFICIAL",
  "channel": "Genshin Impact",
  "video_id": "...",
  "title": "캐릭터 PV - 「푸리나」",
  "published_at": "...",
  "description": "...",
  "language": "ko",
  "transcript_segments": [
    {
      "start": 12.4,
      "end": 18.2,
      "text": "..."
    }
  ],
  "related_entities": ["푸리나", "폰타인"]
}
```

가능해지는 기능:

```text
공식 PV에서 특정 캐릭터가 어떤 상징으로 묘사되는지 분석
데인 여담에서 특정 개념이 어떻게 설명되는지 검색
영상 자막과 게임 내부 텍스트의 표현 차이 비교
특정 모티프가 영상에서 반복되는지 확인
답변 출처를 영상 타임스탬프로 연결
```

주의:

```text
영상 자체를 저장하기보다 메타데이터, 설명문, 자막, 타임스탬프 중심으로 저장한다.
YouTube 자막/스크래핑/재배포는 사용 방식에 따라 약관 또는 저작권 확인이 필요하다. (확인 필요)
```

---

## 4.3 Official Map / Spatial DB

맵 데이터는 일반 텍스트와 다르게 공간 정보가 핵심이다.

수집 대상 후보:

```text
지역
장소
랜드마크
월드 임무 위치
특수 오브젝트
수집 요소
맵 핀 설명
공식 맵의 카테고리 정보
```

저장 대상:

```text
맵 이름
지역
장소 이름
카테고리
설명
좌표
원본 좌표계
정규화 좌표계
관련 엔티티
원본 URL
```

Canonical 예시:

```json
{
  "source": "official_map",
  "source_level": "L0_OFFICIAL",
  "map": "teyvat",
  "region": "폰타인",
  "area": "폰타인성",
  "category": "landmark",
  "name": "오페라 에피클레스",
  "description": "...",
  "coordinates": {
    "raw": {
      "x": 12345,
      "y": 67890,
      "source_coordinate_system": "official_map_internal"
    },
    "normalized": {
      "x": 0.5321,
      "y": 0.2844,
      "system": "teyvat_2d_normalized"
    }
  },
  "related_entities": ["푸리나", "느비예트", "폰타인"]
}
```

가능해지는 기능:

```text
푸리나 관련 장소를 지도에서 확인
폰타인 스토리 핵심 장소를 공간적으로 묶기
특정 개념이 어느 지역에 집중되는지 분석
퀘스트/책/오브젝트/캐릭터의 공간 관계 분석
지역별 모티프 분포 분석
```

기술 방향:

```text
SQLite FTS5: 텍스트 검색
SQLite RTree: 좌표 기반 공간 검색
GeoJSON export: 지도 UI 연동
```

---

## 4.4 External Comparative Frame DB

research 모드에서는 원신 내부 DB만 보지 않고, 외부의 종교·신화·철학·문학 구조를 비교틀로 사용할 수 있다.

이 DB는 공식 설정의 정답지가 아니다. 원신 구조를 해석하기 위한 렌즈다.

수집/정리 후보:

```text
영지주의
기독교적 구원 서사
불교적 윤회/기억/해탈 구조
북유럽 신화의 세계수
그리스 신화의 신과 인간 관계
중국 고전/도교/선계 모티프
일본 신토 모티프
연금술
카발라
운명론
가짜 하늘/세계의 허위성 모티프
```

저장 방식:

```text
원문 전체 수집보다는 요약된 비교 프레임으로 관리
공식 원신 자료와 구분
직접 근거가 아니라 해석 렌즈로 라벨링
```

Canonical 예시:

```json
{
  "source": "comparative_frame",
  "source_level": "L3_COMPARATIVE_FRAME",
  "frame_name": "gnosticism",
  "language": "ko",
  "concepts": ["거짓된 세계", "감춰진 진실", "창조자와 상위 신", "구원"],
  "summary": "...",
  "use_policy": "research_lens_only"
}
```

주의:

```text
외부 비교틀은 공식 설정의 증거가 아니다.
“원신이 이 종교를 그대로 따른다”가 아니라 “구조적 유사성이 있다”로 다룬다.
외부 지식 출처는 별도 검증이 필요하다. (확인 필요)
```

---

## 4.5 Community / Guide DB

커뮤니티 자료와 공략 데이터는 유용하지만, 공식 근거와 섞이면 위험하다. 따라서 후순위로 넣고 출처 등급을 낮게 둔다.

수집 후보:

```text
위키
공략 사이트
커뮤니티 가설
유튜버 분석
Reddit / HoYoLAB / 국내 커뮤니티 글
메타 빌드 정보
```

용도:

```text
guide 라우트에서 캐릭터 사용법 보조
research 라우트에서 기존 커뮤니티 가설 비교
공식 자료와 팬덤 해석의 차이 확인
```

주의:

```text
초기 단계에서는 공식 자료 기반 시스템을 먼저 안정화한다.
커뮤니티 자료는 L4_COMMUNITY로 분리한다.
공식 근거처럼 사용하지 않는다.
```

---

## 4.6 Hypothesis Store

research 라우트가 발전하면 시스템이 생성한 가설을 저장하고 재검토할 수 있어야 한다.

저장 대상:

```text
가설 제목
관련 엔티티
근거 문서
반례 문서
가설 강도
생성 시각
생성한 모델/버전
사용자 피드백
후속 업데이트 여부
```

Canonical 예시:

```json
{
  "hypothesis_id": "hyp_000001",
  "title": "천리는 세계 질서 유지 장치일 수 있다",
  "related_entities": ["천리", "셀레스티아", "강림자", "세계수"],
  "strength": "medium",
  "evidence_refs": ["..."],
  "counter_evidence_refs": ["..."],
  "status": "open",
  "created_by": "research_route",
  "created_at": "..."
}
```

이 저장소는 정답 저장소가 아니라, 연구 가설을 관리하는 워크스페이스다.

---

## 5. Source Level 정책

데이터가 늘어날수록 source level이 중요해진다.

추천 source level:

```text
L0_GAME
게임 클라이언트/Project Amber 기반 공식 게임 내부 데이터

L0_OFFICIAL
공식 웹, 공식 맵, 공식 YouTube, 공식 방송, 공식 만화 등 HoYoverse 공식 공개 자료

L1_DERIVED
공식 자료에서 시스템이 계산/정규화한 정보
예: 좌표 변환, 엔티티 링크, 동시 등장, 번역 차이

L2_INTERPRETED
공식 근거 기반 자체 해석
예: 세계수는 기억 저장소이자 역사 수정 장치처럼 작동한다는 해석

L3_COMPARATIVE_FRAME
외부 비교틀
예: 영지주의, 세계수 신화, 종교적 구원 서사, 연금술

L4_COMMUNITY
커뮤니티 추측, 유튜버 분석, 팬덤 해석, 위키/공략 사이트

L5_AI_SPECULATION
AI 또는 사용자가 만든 창의적 가설
```

라우트별 사용 정책:

| 라우트 | 허용 source level |
|---|---|
| basic_lookup | L0_GAME, 일부 L0_OFFICIAL |
| summary | L0_GAME, L0_OFFICIAL |
| analysis | L0_GAME, L0_OFFICIAL, L1_DERIVED, L2_INTERPRETED |
| research | L0~L5 모두 가능하되 라벨 필수 |
| guide | L0~L4 가능하되 공식/해석/메타 구분 필수 |

---

## 6. Research 모드에서 DB의 역할

`research` 라우트에서 DB는 정답지가 아니다.

`basic_lookup`에서는 DB가 공식 정답의 기준이지만, `research`에서는 DB가 원신 세계관의 구조를 관찰하기 위한 자료가 된다.

research 모드는 공식 자료를 바탕으로 다음을 추출한다.

```text
반복되는 모티프
개념 간 관계
번역 차이
공간적 배치
서사 구조
상징 체계
반복되는 결말/멸망/구원 구조
공식 텍스트의 모순 또는 비어 있는 부분
```

그 다음 외부 비교틀을 사용할 수 있다.

```text
종교
신화
철학
연금술
영지주의
세계수 신화
구원 서사
운명론
```

단, 외부 비교틀은 공식 설정의 정답이 아니라 원신 구조를 해석하기 위한 렌즈로만 사용한다.

research의 목표는 하나의 확정 답변을 내는 것이 아니라, 가능한 가설 공간을 넓히고 각 가설의 근거·약점·반례·추측 강도를 분리해 제시하는 것이다.

---

## 7. Research의 창의성 정책

research 라우트에서는 창의적인 가설 생성을 허용한다.

다만 가설은 반드시 라벨링되어야 한다.

```text
공식 사실
공식 근거 기반 해석
간접 근거 기반 가설
약한 모티프 기반 가설
창의적 확장 가설
순수 상상에 가까운 추측
```

가설 강도 라벨:

```text
강함:
직접 근거가 여러 개 있고 반례가 약함

중간:
간접 근거가 있고 구조적으로 설득력이 있음

약함:
모티프, 상징, 정황 근거 중심

상상적:
흥미롭지만 공식 근거는 부족함
```

research 답변은 다음처럼 구성할 수 있다.

```text
1. 짧은 결론
2. 확정 가능한 공식 사실
3. 원신 내부 구조 분석
4. 외부 비교틀
5. 가능한 가설
6. 각 가설의 근거
7. 각 가설의 약점과 반례
8. 창의적 확장 가설
9. 현재로서는 확정할 수 없는 부분
10. 추가 조사할 자료
```

---

## 8. 통합 DB 구조

최종 DB는 하나의 단순 문서 DB가 아니라, 여러 인덱스를 연결한 구조가 되어야 한다.

```text
documents
공식 텍스트, 웹 문서, 책, 대사, 자막, 기사

chunks
검색용 텍스트 단위

entities
캐릭터, 장소, 세력, 사건, 개념, 아이템, 모티프

media_segments
유튜브 자막/영상 설명/타임스탬프

map_points
좌표가 있는 장소/오브젝트/퀘스트/핀

relations
엔티티 간 관계

evidence_pins
답변에 인용 가능한 근거 단위

hypotheses
research 라우트가 생성/관리하는 가설

comparative_frames
종교/신화/철학 등 외부 비교틀

source_registry
각 자료의 출처, 수집 방식, 신뢰도, 라이선스/주의사항
```

---

## 9. 추천 폴더 구조

```text
data/raw/project_amber/
data/raw/official_web/
data/raw/official_youtube/
data/raw/official_map/
data/raw/comparative_frames/
data/raw/community_optional/

data/canonical/documents/
data/canonical/media/
data/canonical/map/
data/canonical/entities/
data/canonical/relations/
data/canonical/hypotheses/

src/genshin_lore_db/ingest/project_amber.py
src/genshin_lore_db/ingest/official_web.py
src/genshin_lore_db/ingest/official_youtube.py
src/genshin_lore_db/ingest/official_map.py
src/genshin_lore_db/ingest/comparative_frames.py

src/genshin_lore_db/canonical/document.py
src/genshin_lore_db/canonical/media.py
src/genshin_lore_db/canonical/map.py
src/genshin_lore_db/canonical/relation.py
src/genshin_lore_db/canonical/hypothesis.py

src/genshin_lore_db/index/text_index.py
src/genshin_lore_db/index/media_index.py
src/genshin_lore_db/index/map_index.py
src/genshin_lore_db/index/graph_index.py
src/genshin_lore_db/index/motif_index.py
```

---

## 10. 구현 우선순위

지금 당장 모든 데이터를 수집하면 안 된다. 우선순위가 필요하다.

### 1단계: Project Amber 안정화

```text
basic_lookup 정확도 개선
캐릭터/무기/성유물 facts 확장
validator 강화
Source Reader 구현
평가셋 확대
```

### 2단계: Official Web / YouTube 텍스트 인덱스

```text
공식 웹 문서 parser
공식 YouTube 메타데이터 parser
자막/설명문 segment index
영상 타임스탬프 source link
```

이 단계가 맵보다 우선이다. 텍스트와 자막은 summary, analysis, research에 바로 도움이 되기 때문이다.

### 3단계: Official Map / Spatial DB

```text
공식 맵 raw dump
좌표 스키마 정의
좌표 정규화
RTree 공간 인덱스
GeoJSON export
장소-엔티티 연결
```

### 4단계: Graph / Motif Index

```text
엔티티 관계 그래프
모티프 사전
co-occurrence index
translation diff
counter-evidence search
```

### 5단계: Comparative Frame DB

```text
종교/신화/철학/연금술 비교틀 정리
research 라우트에서만 사용
공식 근거와 명확히 분리
```

### 6단계: Community / Guide Data

```text
공략 사이트
위키
커뮤니티 가설
메타 빌드 자료
```

공식 자료 기반 시스템이 안정화된 뒤 추가한다.

---

## 11. API 구상

나중에 필요한 API 예시:

```text
POST /search
POST /investigate
POST /answer
POST /research
GET /source/{document_id}
GET /source/{document_id}/window
GET /media/{video_id}/segments
GET /media/{video_id}/timestamp/{time}
GET /map/points?entity=...
GET /map/nearby?x=...&y=...&radius=...
GET /graph/entity/{entity_id}
GET /hypotheses/{hypothesis_id}
```

---

## 12. 주의사항

### 12.1 raw data 공개 금지

공식 웹, YouTube, 맵, 커뮤니티 자료는 약관/저작권 문제가 있을 수 있다. 공개 GitHub에는 parser, schema, docs만 올리고 raw data는 로컬 또는 개인 DB에 보관한다.

```text
공개 저장소:
코드, 스키마, 문서, 샘플

비공개/로컬:
raw dump, full transcript, 대량 수집 데이터
```

### 12.2 출처와 수집 시각 보존

모든 자료는 다음 정보를 보존해야 한다.

```text
source
source_level
source_url
retrieved_at
language
raw_ref
parser_version
canonical_version
```

### 12.3 공식과 추측 분리

특히 research에서는 외부 비교틀과 창의적 가설이 들어올 수 있다. 따라서 답변과 내부 데이터 모두에서 공식 사실과 추측을 강하게 분리해야 한다.

---

## 13. 최종 정리

현재 Project Amber DB는 원신 공식 텍스트 기반 시스템의 핵심 출발점이다. 그러나 최종 목표인 대화형 원신 스토리 연구 AI를 만들려면 다음 DB가 추가되어야 한다.

```text
Official Web DB
Official YouTube / Media DB
Official Map / Spatial DB
External Comparative Frame DB
Community / Guide DB
Hypothesis Store
```

이 중 우선순위는 다음과 같다.

```text
1. Project Amber 안정화
2. Official Web / YouTube 텍스트 인덱스
3. Official Map / Spatial DB
4. Graph / Motif Index
5. Comparative Frame DB
6. Community / Guide DB
7. Hypothesis Store 고도화
```

가장 중요한 관점은 이것이다.

```text
basic_lookup에서 DB는 정답지다.
research에서 DB는 정답지가 아니라 원신 세계관의 구조를 관찰하는 자료다.
```

따라서 research 라우트는 공식 자료를 바탕으로 구조를 파악하고, 종교·신화·철학 같은 외부 비교틀까지 활용해 창의적인 가설을 만들 수 있다. 단, 모든 가설은 근거 수준과 불확실성을 명확히 표시해야 한다.
