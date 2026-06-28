# 데이터 파이프라인

데이터 파이프라인은 `수집 → RAW 보존 → 사람이 읽는 복사본 생성 → canonical 정규화 → RAG/검색 인덱스 생성` 순서로 구성됩니다.

v0.6부터는 기존 v1 산출물을 유지하면서 Project Amber 전용 v2 산출물을 병행 생성합니다. v2의 메인 소스는 Project Amber이고, TextMap은 보조 검색/번역 테이블로만 포함합니다.

## 데이터 출처

```text
Project Amber
- 캐릭터
- 무기
- 성유물
- TCG
- 여행 기록
- 업적
- 음식
- 재료
- 장식
- 명함
- 생물
- 서적
- 가이드북
- 기타 상세 데이터

Dimbreath/AnimeGameData TextMap
- TextMapKR.json
- TextMapCHS.json
- TextMapJP.json
- TextMapEN.json
```

수집 대상은 프로젝트 목적상 한중일영을 모두 포함합니다.

## 산출물 구조

```text
data/
  raw/
    project_amber/
    dimbreath_textmap/

  processed/
    project_amber/
    project_amber_readable_v2/
    rag/
    entities/
    search/
    search_v2/
    search_engine/
    quality/
    schema/

  canonical/
    documents.jsonl
    chunks.jsonl
    entity_names.jsonl
    source_links.jsonl
    textmap_entries.jsonl
    build_report.json
    project_amber_v2/
      items.jsonl
      localizations.jsonl
      documents.jsonl
      sections.jsonl
      text_units.jsonl
      relations.jsonl
      entity_names.jsonl
      textmap_entries.jsonl
      build_report.json
```

`data/raw/`는 원본 응답 보존용입니다. 사람이 읽기 좋게 바꾼 파일이나 검색용 인덱스는 `processed`와 `canonical` 아래에 따로 만듭니다.

## 현재 데이터 규모

```text
canonical documents: 79,773
canonical chunks: 149,824
entity_names: 31,036
source_links: 79,773
textmap_entries: 959,510

RAG documents: 79,773
RAG chunks: 149,824
exact duplicate groups: 351
parallel groups: 17,783

entity concepts: 17,447
entity aliases: 73,327
```

## 주요 빌드 명령

전체 흐름:

```powershell
python scripts/crawl_project_amber.py
python scripts/crawl_project_amber_deep.py
python scripts/crawl_project_amber_extras.py
python scripts/crawl_dimbreath_textmap.py

python scripts/build_project_amber_processed.py
python scripts/build_project_amber_v2.py
python scripts/build_canonical.py
python scripts/build_rag_assets.py
python scripts/build_entity_aliases.py
python scripts/build_search_engine_assets.py
python scripts/eval_search_engine.py
python scripts/eval_search_engine.py --db-version v1
```

검색엔진만 다시 빌드:

```powershell
python scripts/build_entity_aliases.py
python scripts/build_search_engine_assets.py
```

개발 중 빠른 검색 확인:

```powershell
python scripts/lore_search_engine.py search "천리" --limit 5
python scripts/lore_search_engine.py investigate "파네스와 천리의 관계" --limit 12
python scripts/search_lore.py "민들레밭의 여우" --language ko --content-type book --limit 5
python scripts/search_lore.py --db-version v1 "천리" --limit 5
```

## Project Amber v2

v2는 기존 `data/processed/project_amber`, `data/canonical`, `data/processed/search`를 덮어쓰지 않습니다.

관련 구현은 `src/genshin_lore_db/pipeline/project_amber_v2.py`에 있습니다. 기존 `src/genshin_lore_db/project_amber_v2.py`는 import 호환용 래퍼입니다.

```text
data/processed/project_amber_readable_v2/
  ko/
  en/
  ja/
  zh-Hans/
  und/

data/canonical/project_amber_v2/
  items.jsonl
  localizations.jsonl
  documents.jsonl
  sections.jsonl
  text_units.jsonl
  relations.jsonl
  entity_names.jsonl
  textmap_entries.jsonl

data/processed/search_v2/
  project_amber_search.sqlite3
```

readable v2의 폴더명은 언어별 번역명이 아니라 `book`, `quest`, `avatar`, `weapon` 같은 안정적인 코드명으로 고정합니다. 파일명에는 ID와 해당 언어 제목을 함께 둡니다.

```text
ko/book/1 - 민들레밭의 여우/00 - 100188 - 민들레밭의 여우·1권.json
ko/reliquary/10001 - 행자의 마음/pieces/1 - EQUIP_RING - 이국의 술잔.json
ko/weapon/11301 - 차가운 칼날/story/00 - 차가운 칼날.json
ko/avatar/10000003 - 진/stories.json
ko/avatar/10000003 - 진/quotes.json
ko/material/140001 - 최초의 날개/story/00 - 최초의 날개.json
ko/quest/aq/1606 - 공월의 노래 제6막 - 아침 안개 속에서 흩어진 달빛.json
```

v2에서는 `_보충 데이터` 폴더를 만들지 않습니다. 책 본문, 성유물 부위 스토리, 무기 스토리, 캐릭터 스토리/대사/코스튬, 재료 스토리는 모두 부모 항목의 하위 문서로 승격됩니다.

## RAW와 전처리 데이터

RAW 데이터는 가능한 그대로 보존합니다.

```text
RAW
- API 응답 원문
- 재처리 가능한 기준 자료
- 직접 수정하지 않음

Processed
- 사람이 읽기 쉬운 파일명
- Project Amber의 UI 구조에 가까운 폴더 구조
- JSON 내용은 보존하되 탐색성을 개선

Canonical
- 검색/RAG/분석을 위한 통합 스키마
- 문서, 청크, 엔티티명, 출처 링크로 분리
```

## GitHub 업로드 정책

대용량 생성 데이터는 저장소에 직접 올리지 않는 방향이 안전합니다.

```text
커밋 대상:
- src/
- scripts/
- config/
- docs/
- schemas/
- README.md
- pyproject.toml

제외 대상:
- data/raw/
- data/canonical/
- data/processed/
- SQLite 인덱스
- 대용량 JSONL 산출물
```

필요하면 나중에 샘플 데이터만 별도 디렉터리로 작게 만들어 커밋하는 방식이 좋습니다.
