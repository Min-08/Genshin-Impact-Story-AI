# Data Expansion and Multi-Scout Retrieval Vision

## 1. 문서 목적

이 문서는 Genshin Impact Story AI에서 앞으로 필요한 DB 확장 방향과 `summary`, `analysis`, `research` 라우트의 탐색 구조를 정의한다.

기존 논의에서 단순히 “요약 색인을 만들자”는 수준을 넘어서, 다음 결론에 도달했다.

```text
요약 색인은 필요하다.
하지만 요약 색인만 훑으면 AI가 유저가 놓친 단서를 찾는 능력이 약해진다.

따라서 summary index는 초반 탐색용 지도이고,
research 라우트는 summary / raw / vector / motif / graph / translation / counter search를 병렬로 돌리는 Multi-Scout 구조가 되어야 한다.
```

이 문서는 기존의 DB 확장 문서와 Summary Index 문서를 대체할 수 있는 통합 설계 문서로 사용한다.

추천 저장 위치:

```text
docs/DATA_AND_RETRIEVAL_VISION.md
```

---

## 2. 현재 DB의 위치

현재 프로젝트의 핵심 DB는 Project Amber 스크래핑 데이터에 기반한다.

Project Amber는 다음 영역에 강하다.

```text
캐릭터
무기
성유물
아이템
책
TextMap
게임 내부 공식 문구
일부 스토리/대사 계열 텍스트
```

이 데이터는 `basic_lookup`과 공식 원문 검색의 핵심 기반이다.

예시:

```text
푸리나의 원소는 무엇인가?
안개를 가르는 회광의 무기 효과는 무엇인가?
절연의 기치 4세트 효과는 무엇인가?
특정 책 원문에 어떤 문장이 있는가?
```

이런 질문에서는 DB가 사실상 정답지 역할을 한다.

하지만 최종 목표인 대화형 원신 스토리 연구 AI를 만들기에는 Project Amber만으로는 부족하다. 원신의 세계관은 게임 내부 텍스트뿐 아니라 공식 영상, 공식 웹 문서, 공식 맵, 이벤트 페이지, PV, 방송, 공간 배치, 외부 신화/종교/철학 구조와의 비교를 통해 더 깊게 해석될 수 있기 때문이다.

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

특징:

```text
DB와 규칙이 정답을 결정한다.
LLM은 말투만 다듬는다.
추측과 추천은 금지한다.
필수 필드 누락 검증이 중요하다.
```

---

### 3.2 summary

```text
DB = 요약할 원문 + 초반 탐색용 지도
```

특정 캐릭터 스토리, 문서, 임무, 개념을 요약한다.

예시:

```text
푸리나 캐릭터 스토리 요약
세계수와 기억 조작 요약
운명의 베틀 개념 정리
폰타인 마신임무 요약
```

summary 라우트에서는 먼저 summary index로 관련 범위를 잡고, 필요하면 원문으로 들어가 확인한다.

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

analysis에서는 공식 사실과 해석을 분리해야 한다.

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

현재 Project Amber 기반 DB에 더해 다음 DB가 필요하다.

```text
Official Web DB
Official YouTube / Media DB
Official Map / Spatial DB
Summary Index DB
Discovery / Clue Index DB
Graph / Motif DB
Translation Diff DB
External Comparative Frame DB
Community / Guide DB
Hypothesis Store
```

---

## 5. Official Web DB

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

## 6. Official YouTube / Media DB

원신은 공식 영상에서 스토리, 상징, 캐릭터 해석, 떡밥을 많이 제공한다. 따라서 공식 YouTube와 영상 자료는 research와 analysis에서 중요하다.

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

## 7. Official Map / Spatial DB

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

## 8. Summary Index DB

Summary Index는 원문을 대체하지 않는다.

Summary Index는 원문 위에 올라가는 **초반 탐색용 지도**다.

```text
사용자 질문
→ 요약 색인에서 관련 문서/사건/장면 후보 탐색
→ 후보 문서의 원문 구간을 Source Reader로 읽기
→ 원문 기반 Evidence Pack 생성
→ 답변 생성
```

핵심 원칙:

```text
Summary Index로 찾고,
Raw Source로 확인하고,
Evidence Pack으로 고정하고,
Answer Writer가 답변한다.
```

---

### 8.1 Summary Index 계층

```text
Level 0: Raw Text Index
- 원문 대사
- 책 원문
- 캐릭터 스토리 원문
- 아이템 설명
- TextMap 원문

Level 1: Segment Summary Index
- 장면 단위 요약
- 대화 묶음 요약
- 퀘스트 단계 요약

Level 2: Document Summary Index
- 임무 하나의 전체 요약
- 책 한 권의 전체 요약
- 캐릭터 스토리 전체 요약

Level 3: Arc / Topic Summary Index
- 폰타인 마신임무 전체 요약
- 세계수 관련 사건 요약
- 강림자 관련 개념 요약
- 특정 캐릭터 서사 요약

Level 4: Research Map Index
- 모티프 요약
- 개념 관계 요약
- 가설 후보 요약
- 반례 후보 요약
```

처음부터 모든 계층을 만들 필요는 없다. 우선 Level 1~2만 도입해도 효과가 크다.

---

### 8.2 document_summaries

```sql
CREATE TABLE document_summaries (
    summary_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    source_level TEXT NOT NULL,
    summary_type TEXT NOT NULL,
    language TEXT NOT NULL,
    title TEXT,
    short_summary TEXT,
    long_summary TEXT,
    key_events_json TEXT,
    key_entities_json TEXT,
    key_concepts_json TEXT,
    motifs_json TEXT,
    source_document_refs_json TEXT,
    model_name TEXT,
    prompt_version TEXT,
    generated_at TEXT,
    validation_status TEXT
);
```

---

### 8.3 segment_summaries

```sql
CREATE TABLE segment_summaries (
    segment_summary_id TEXT PRIMARY KEY,
    document_id TEXT NOT NULL,
    segment_id TEXT NOT NULL,
    source_level TEXT NOT NULL,
    language TEXT NOT NULL,
    sequence_index INTEGER,
    title TEXT,
    summary TEXT,
    key_entities_json TEXT,
    key_concepts_json TEXT,
    motifs_json TEXT,
    raw_start_ref TEXT,
    raw_end_ref TEXT,
    model_name TEXT,
    prompt_version TEXT,
    generated_at TEXT,
    validation_status TEXT
);
```

---

### 8.4 topic_summaries

```sql
CREATE TABLE topic_summaries (
    topic_summary_id TEXT PRIMARY KEY,
    topic_id TEXT NOT NULL,
    source_level TEXT NOT NULL,
    language TEXT NOT NULL,
    title TEXT,
    overview TEXT,
    related_entities_json TEXT,
    related_documents_json TEXT,
    direct_evidence_refs_json TEXT,
    indirect_evidence_refs_json TEXT,
    counter_evidence_refs_json TEXT,
    motifs_json TEXT,
    confidence TEXT,
    model_name TEXT,
    prompt_version TEXT,
    generated_at TEXT,
    validation_status TEXT
);
```

---

## 9. Summary Index의 한계

요약 색인은 강력하지만, 요약만 보면 AI가 유저가 놓친 단서를 찾는 능력이 약해질 수 있다.

이유는 요약이 원문을 압축하면서 다음 정보를 잃을 수 있기 때문이다.

```text
작은 떡밥
상징적 표현
반복 모티프
번역 차이
특이한 단어 선택
반례성 문장
한 번만 등장하는 핵심 단서
```

예를 들어 원문에 이런 표현이 있다고 하자.

```text
하늘의 질서는 다시 흔들리지 않을 것이다.
```

요약본에는 이것이 다음처럼 압축될 수 있다.

```text
사건이 마무리되고 질서가 회복된다.
```

이 경우 “하늘”, “질서”, “천리”, “통제 구조” 같은 떡밥이 요약에서 사라질 수 있다.

따라서 research 라우트는 Summary Index만 보면 안 된다.

---

## 10. Discovery / Clue Index DB

Summary Index가 내용을 압축하는 계층이라면, Discovery / Clue Index는 원문에서 **찾을 만한 단서 태그를 많이 붙이는 계층**이다.

요약이 아니라 “발견 가능성”을 높이기 위한 인덱스다.

저장 대상:

```text
문서별 핵심 엔티티
문서별 핵심 개념
문서별 모티프
문서별 이상한 표현
문서별 다국어 표현 차이
문서별 동시 등장 관계
문서별 떡밥 후보
문서별 반례 후보
```

Canonical 예시:

```json
{
  "document_id": "quest_xxx",
  "motifs": ["하늘", "왕좌", "심판", "운명"],
  "entities": ["푸리나", "느비예트", "셀레스티아"],
  "possible_clues": [
    "하늘의 질서라는 표현이 등장함",
    "심판과 무대 모티프가 함께 등장함",
    "한국어와 영어 표현의 뉘앙스가 다름"
  ],
  "source_refs": [
    {
      "document_id": "quest_xxx",
      "start": 120,
      "end": 180
    }
  ]
}
```

Discovery Index는 research에서 “유저가 직접 떠올리지 못한 후보”를 찾는 데 중요하다.

---

## 11. Graph / Motif DB

research에서 중요한 것은 단어 일치만이 아니다. 개념 간 관계, 모티프 반복, 공간 배치, 동시 등장 구조가 필요하다.

Graph / Motif DB는 다음을 저장한다.

```text
엔티티 간 관계
개념 간 관계
모티프 출현 위치
문서별 동시 등장
장소별 모티프 분포
시간/버전별 개념 변화
```

예시 관계:

```text
푸리나 --associated_with--> 폰타인
푸리나 --appears_in--> 마신임무 4장
오페라 에피클레스 --located_in--> 폰타인
오페라 에피클레스 --associated_with--> 재판
재판 --motif_related_to--> 심판
심판 --possibly_related_to--> 천리
```

research에서 이런 그래프는 질문에 직접 나오지 않은 주변 개념을 찾는 데 사용된다.

---

## 12. Translation Diff DB

원신은 다국어 표현 차이가 떡밥이 될 수 있다. 따라서 번역 차이도 별도 인덱스로 관리해야 한다.

저장 대상:

```text
같은 TextMap ID의 한국어/중국어/일본어/영어 표현
의미 차이가 큰 단어
고유명사 번역 차이
종교/신화적 뉘앙스 차이
직역/의역 차이
스토리 해석에 영향을 주는 차이
```

용도:

```text
research에서 모호한 개념의 원문 뉘앙스 확인
번역에서 사라진 떡밥 탐색
특정 단어가 언어별로 어떻게 다르게 표현되는지 비교
```

---

## 13. External Comparative Frame DB

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

## 14. Community / Guide DB

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

## 15. Hypothesis Store

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

## 16. Source Level 정책

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

L1_DERIVED_SUMMARY
공식 원문에서 생성된 요약

L2_INTERPRETED
공식 근거 기반 자체 해석
예: 세계수는 기억 저장소이자 역사 수정 장치처럼 작동한다는 해석

L2_INTERPRETED_SUMMARY
여러 공식 문서를 묶어 해석적으로 정리한 요약

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
| summary | L0_GAME, L0_OFFICIAL, L1_DERIVED_SUMMARY |
| analysis | L0_GAME, L0_OFFICIAL, L1_DERIVED, L1_DERIVED_SUMMARY, L2_INTERPRETED |
| research | L0~L5 모두 가능하되 라벨 필수 |
| guide | L0~L4 가능하되 공식/해석/메타 구분 필수 |

---

## 17. Summary 라우트 탐색 구조

summary 라우트는 research보다 단순하지만, 질문의 구체성에 따라 원문 진입 정도가 달라져야 한다.

### 17.1 넓은 summary 질문

예시:

```text
폰타인 마신임무 요약해줘
푸리나 캐릭터 스토리 요약해줘
세계수 기억 조작 요약해줘
```

처리:

```text
summary index에서 관련 문서 범위 파악
→ document summary / segment summary로 전체 구조 확인
→ 중요한 구간만 raw source로 확인
→ 최종 요약 작성
```

이 경우 모든 원문을 다 읽을 필요는 없다. 요약 색인을 기반으로 큰 구조를 잡고, 핵심 구간만 원문 확인한다.

---

### 17.2 구체적인 summary 질문

예시:

```text
푸리나가 자기 정체를 드러내는 장면 요약해줘
세계수 기억 조작이 실제로 언급된 부분만 알려줘
나히다가 룩카데바타를 어떻게 설명했는지 요약해줘
```

처리:

```text
summary index로 후보 장면 찾기
→ 바로 raw source로 drill-down
→ 해당 장면 주변 문맥 읽기
→ 원문 기반으로 요약
```

구체적인 질문에서는 summary index가 후보 찾기 역할을 하고, 최종 요약은 원문 중심으로 만든다.

---

### 17.3 Summary 라우트 내부 모드

```text
overview_summary
- 전체 요약
- summary index 중심
- raw spot-check

focused_summary
- 특정 장면/캐릭터/개념 요약
- summary index + raw drill-down

source_summary
- 특정 원문 범위 요약
- raw source 중심

comparative_summary
- 여러 문서 비교 요약
- summary index로 후보 선택 후 raw 확인
```

---

## 18. Research 라우트의 Multi-Scout 구조

research 라우트는 summary index만 보면 안 된다.

research에서는 여러 탐색 채널을 병렬로 돌린다.

```text
Scout A: Summary Scout
- topic summary, document summary에서 큰 구조 탐색

Scout B: Raw Keyword Scout
- 원문에서 명시 키워드와 확장 키워드 직접 검색

Scout C: Semantic Scout
- 단어가 달라도 의미가 비슷한 문장 검색

Scout D: Motif Scout
- 하늘, 왕좌, 심판, 금지된 지식, 기억, 세계수 같은 모티프 검색

Scout E: Entity Graph Scout
- 엔티티 관계를 따라 주변 개념 확장

Scout F: Translation Diff Scout
- 다국어 표현 차이와 번역 뉘앙스 탐색

Scout G: Counter-evidence Scout
- 가설에 불리한 근거 탐색

Scout H: External Frame Scout
- 영지주의, 종교적 세계 구조, 세계수 신화 같은 비교틀에서 탐색 키워드 생성
```

이 구조의 목적은 유저가 직접 떠올리지 못한 연결을 AI가 병렬로 탐색하도록 만드는 것이다.

---

## 19. Research 탐색 흐름

```text
1. Query Understanding
   질문에서 대상, 개념, 외부 비교틀, 추측 허용 여부를 뽑는다.

2. Seed Generation
   명시 키워드 + 별칭 + 관련 개념 + 모티프 + 외부 비교틀 키워드를 만든다.

3. Parallel Scout Search
   summary / raw / vector / motif / graph / translation / counter / external frame 검색을 병렬 수행한다.

4. Candidate Merge
   각 scout 결과를 통합하고 중복 제거한다.

5. Candidate Scoring
   엔티티 일치, 모티프 일치, source level, 그래프 거리, 다양성, 반례 가능성을 점수화한다.

6. Raw Drill-down
   상위 후보의 원문으로 들어가 주변 문맥을 읽는다.

7. Evidence Pinning
   원문에서 실제 근거 구간을 고정한다.

8. Expansion Loop
   원문에서 새로 발견한 개념을 seed로 추가해 다시 검색한다.

9. Counter Search
   가설에 불리한 근거를 별도로 찾는다.

10. Hypothesis Build
   공식 사실, 구조 해석, 강한 가설, 약한 가설, 창의적 확장 가설을 분리한다.

11. Validation
   추측이 공식 사실처럼 포장되었는지, 반례가 누락되었는지 검사한다.
```

한 줄 요약:

```text
Summary로 넓게 정찰하고,
Raw로 직접 확인하고,
Graph/Motif/Vector로 숨은 연결을 찾고,
Counter Search로 반례를 찾고,
그 결과를 가설로 조립한다.
```

---

## 20. Candidate Scoring

요약 색인 또는 scout 결과가 후보를 반환하면 다음 기준으로 점수화한다.

```text
엔티티 직접 일치
별칭 일치
제목 일치
핵심 개념 일치
모티프 일치
같은 지역/임무/시대
공식 source level
이미 발견한 evidence와의 연결성
그래프 거리
반례 후보로서의 가치
다른 후보들과의 다양성
```

예시:

```text
score =
  entity_overlap * 3.0
+ alias_match * 2.5
+ motif_overlap * 1.5
+ title_match * 2.0
+ source_level_weight
+ graph_distance_bonus
+ diversity_bonus
+ counter_evidence_bonus
```

research에서는 “정답에 가까운 문서”만 찾으면 안 된다. 연결될 수도 있는 주변 문서와 반례도 필요하므로 diversity와 counter_evidence를 점수에 반영해야 한다.

---

## 21. Query Expansion 정책

research에서는 “일치”의 의미가 넓어야 한다.

basic_lookup에서는 일치가 엄격하다.

```text
푸리나 = 푸리나
천리 = 천리
```

research에서는 관련 개념까지 확장한다.

예시:

```text
천리
→ 하늘
→ 셀레스티아
→ 왕좌
→ 운명
→ 질서
→ 강림자
→ 세계의 법칙
→ 거짓된 하늘
→ 파네스
→ 네 그림자
```

확장 방식:

```text
DB 기반 확장:
실제로 같이 등장한 단어/엔티티

LLM 기반 확장:
세계관적으로 관련 가능성이 있는 단어/모티프

외부 비교틀 기반 확장:
종교/신화/철학 구조에서 유래한 비교 키워드
```

---

## 22. Research 창의성 정책

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

research 답변은 창의성을 막지 않는다. 대신 그 창의성이 어디까지나 가설인지, 근거 강도는 어느 정도인지, 반례는 무엇인지 표시한다.

---

## 23. 통합 DB 구조

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

document_summaries
문서 단위 요약

segment_summaries
장면/대화 묶음 단위 요약

topic_summaries
개념/주제 단위 요약

discovery_clues
문서별 단서, 떡밥, 이상 표현, 모티프 태그

relations
엔티티 간 관계

motifs
반복 상징과 모티프 정의

translation_diffs
다국어 표현 차이

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

## 24. 추천 폴더 구조

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
data/canonical/summaries/
data/canonical/discovery/
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
src/genshin_lore_db/canonical/summary.py
src/genshin_lore_db/canonical/discovery.py
src/genshin_lore_db/canonical/relation.py
src/genshin_lore_db/canonical/hypothesis.py

src/genshin_lore_db/index/text_index.py
src/genshin_lore_db/index/summary_index.py
src/genshin_lore_db/index/media_index.py
src/genshin_lore_db/index/map_index.py
src/genshin_lore_db/index/graph_index.py
src/genshin_lore_db/index/motif_index.py
src/genshin_lore_db/index/translation_diff_index.py

src/genshin_lore_db/search_engine/scouts/
src/genshin_lore_db/search_engine/scouts/summary_scout.py
src/genshin_lore_db/search_engine/scouts/raw_keyword_scout.py
src/genshin_lore_db/search_engine/scouts/semantic_scout.py
src/genshin_lore_db/search_engine/scouts/motif_scout.py
src/genshin_lore_db/search_engine/scouts/graph_scout.py
src/genshin_lore_db/search_engine/scouts/translation_scout.py
src/genshin_lore_db/search_engine/scouts/counter_scout.py
src/genshin_lore_db/search_engine/scouts/external_frame_scout.py
```

---

## 25. 구현 우선순위

지금 당장 모든 데이터를 수집하면 안 된다. 우선순위가 필요하다.

### 1단계: Project Amber 안정화

```text
basic_lookup 정확도 개선
캐릭터/무기/성유물 facts 확장
validator 강화
Source Reader 구현
평가셋 확대
```

---

### 2단계: Summary Index + Raw Drill-down

```text
document_summaries 생성
segment_summaries 생성
summary index 구축
summary → raw source 연결
Source Reader와 Evidence Pin 연결
```

---

### 3단계: Multi-Scout Research 기반

```text
raw keyword scout
summary scout
motif scout
graph scout 초안
counter-evidence scout 초안
candidate merge/ranking
research expansion loop
```

---

### 4단계: Official Web / YouTube 텍스트 인덱스

```text
공식 웹 문서 parser
공식 YouTube 메타데이터 parser
자막/설명문 segment index
영상 타임스탬프 source link
```

텍스트와 자막은 summary, analysis, research에 바로 도움이 되기 때문에 맵보다 우선한다.

---

### 5단계: Official Map / Spatial DB

```text
공식 맵 raw dump
좌표 스키마 정의
좌표 정규화
RTree 공간 인덱스
GeoJSON export
장소-엔티티 연결
```

---

### 6단계: Translation Diff / Motif / Graph 고도화

```text
다국어 표현 차이 분석
모티프 사전
co-occurrence index
entity relation graph
counter-evidence search 고도화
```

---

### 7단계: Comparative Frame DB

```text
종교/신화/철학/연금술 비교틀 정리
research 라우트에서만 사용
공식 근거와 명확히 분리
```

---

### 8단계: Community / Guide Data

```text
공략 사이트
위키
커뮤니티 가설
메타 빌드 자료
```

공식 자료 기반 시스템이 안정화된 뒤 추가한다.

---

## 26. CLI 예시

```powershell
python scripts\build_document_summaries.py --source project_amber --lang ko
python scripts\build_segment_summaries.py --content-type quest --lang ko
python scripts\build_topic_summaries.py --topics config\lore_topics.json --lang ko
python scripts\build_summary_index.py

python scripts\build_discovery_index.py --source project_amber --lang ko
python scripts\build_motif_index.py --config config\motifs.json
python scripts\build_graph_index.py
python scripts\build_translation_diff_index.py

python scripts\lore_search_engine.py search "푸리나 스토리 역할" --scope summary
python scripts\lore_search_engine.py investigate "파네스와 천리 관계" --scope summary,raw
python scripts\lore_search_engine.py research "천리와 영지주의 구조 비교" --multi-scout
```

---

## 27. API 구상

```text
POST /search
POST /investigate
POST /answer
POST /research

GET /source/{document_id}
GET /source/{document_id}/window

GET /summary/document/{document_id}
GET /summary/topic/{topic_id}

GET /media/{video_id}/segments
GET /media/{video_id}/timestamp/{time}

GET /map/points?entity=...
GET /map/nearby?x=...&y=...&radius=...

GET /graph/entity/{entity_id}
GET /hypotheses/{hypothesis_id}
```

---

## 28. 주의사항

### 28.1 raw data 공개 금지

공식 웹, YouTube, 맵, 커뮤니티 자료는 약관/저작권 문제가 있을 수 있다. 공개 GitHub에는 parser, schema, docs만 올리고 raw data는 로컬 또는 개인 DB에 보관한다.

```text
공개 저장소:
코드, 스키마, 문서, 샘플

비공개/로컬:
raw dump, full transcript, 대량 수집 데이터
```

---

### 28.2 출처와 수집 시각 보존

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

---

### 28.3 요약은 최종 근거가 아니다

Summary Index는 탐색에 사용하고, 최종 답변의 근거는 원문 Evidence Pin으로 고정한다.

---

### 28.4 공식과 추측 분리

특히 research에서는 외부 비교틀과 창의적 가설이 들어올 수 있다. 따라서 답변과 내부 데이터 모두에서 공식 사실과 추측을 강하게 분리해야 한다.

---

## 29. 최종 정리

이 문서의 핵심은 다음이다.

```text
Project Amber는 공식 게임 텍스트 DB의 출발점이다.
하지만 최종 연구 AI에는 Official Web, YouTube, Map, Summary Index, Discovery Index, Graph/Motif, Translation Diff, Comparative Frame이 필요하다.

Summary Index는 초반 탐색에 필요하지만,
Summary Index만 훑으면 AI가 유저가 놓친 단서를 찾는 능력이 약해진다.

따라서 research 라우트는 Multi-Scout 구조가 되어야 한다.
```

최종 구조:

```text
Summary Index = 지도
Raw Index = 실제 지형
Vector Index = 의미상 비슷한 길
Motif Index = 상징적 연결
Graph Index = 관계망
Translation Diff = 언어 차이 단서
Counter Search = 반례 탐색
External Frame = 해석 렌즈
```

Summary 라우트는 질문의 구체성에 따라 summary 중심과 raw 중심을 전환한다.

Research 라우트는 summary / raw / vector / motif / graph / translation / counter / external frame scout를 병렬로 돌리고, 그 결과를 원문 근거로 확인한 뒤 가설을 만든다.

최종 원칙:

```text
Summary로 넓게 정찰하고,
Raw로 깊게 확인하고,
Graph/Motif/Vector로 숨은 연결을 찾고,
Counter Search로 반례를 찾고,
Evidence Pack으로 고정하고,
Answer Writer가 공식 사실·해석·추측을 분리해 답변한다.
```
