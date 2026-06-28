# Project Amber DB Builder

Project Amber를 크롤링해서 로컬 DB를 만드는 독립 실행용 패키지입니다.

목표는 이 폴더만 공유해도 받는 사람이 `build_amber_db.cmd`를 실행해서 원본 RAW, canonical JSONL, 사람이 읽는 JSON, SQLite 검색 DB까지 한 번에 만들 수 있게 하는 것입니다. 원래 연구 프로젝트의 QA, 라우터, 문서, 테스트, 연구 노트는 포함하지 않았습니다.

## 한 번에 실행

Windows에서는 이 파일을 더블클릭합니다.

```text
build_amber_db.cmd
```

PowerShell에서 직접 실행하려면:

```powershell
.\build_amber_db.ps1
```

공통 Python 진입점은 다음입니다.

```powershell
python build_amber_db.py
```

먼저 실행될 명령만 확인하려면:

```powershell
python build_amber_db.py --dry-run
```

## 만들어지는 결과

```text
data/raw/project_amber/
  Project Amber API 원본 응답

data/raw/dimbreath_textmap/
  TextMapKR/CHS/JP/EN 원본 응답

data/processed/project_amber_readable_v2/
  사람이 읽기 쉬운 Project Amber JSON 사본

data/canonical/project_amber_v2/
  items/localizations/documents/sections/text_units/relations JSONL

data/processed/search_v2/project_amber_search.sqlite3
  SQLite FTS5 검색 DB
```

TextMap은 Project Amber DB의 보조 검색/번역 테이블로 기본 포함합니다. Project Amber만 받고 싶으면 `--no-textmap`을 붙입니다.

```powershell
python build_amber_db.py --no-textmap
```

## 기본 수집 대상

언어:

```text
ko, zh-Hans, ja, en
```

Project Amber content type:

```text
quest, avatar, weapon, gcg, reliquary, book, material, food,
furniture, furnitureSuite, monster, namecard, achievement, elements
```

보강 수집:

```text
book readable text
weapon story
reliquary piece story
avatar fetter / costume story
material / food story
extras / static / advanced guide data
```

일부만 만들 때:

```powershell
python build_amber_db.py --languages ko en --content-types book weapon avatar
```

이미 RAW가 있고 DB만 다시 만들 때:

```powershell
python build_amber_db.py --skip-crawl
```

기존 RAW를 강제로 다시 받을 때:

```powershell
python build_amber_db.py --force
```

## 검색 확인

DB 생성 후:

```powershell
python search_amber_db.py "민들레밭의 여우" --language ko --content-type book --limit 5
python search_amber_db.py "니벨룽겐" --language ko --limit 5
```

## 실행 순서

`build_amber_db.py`는 내부적으로 다음 단계를 실행합니다.

```text
1. Project Amber 목록 수집
2. Project Amber 상세 데이터 병렬 수집
3. Project Amber deep text 병렬 수집
4. Project Amber extras/static/advanced 데이터 병렬 수집
5. TextMap 수집
6. Project Amber v2 readable/canonical/SQLite 빌드
7. JSONL/SQLite audit
```

## 주의

전체 수집과 빌드는 오래 걸리고 결과 데이터가 GB 단위로 커질 수 있습니다. 이 패키지는 프로그램만 공유하는 용도이며, 수집된 원본 데이터나 생성 DB를 기본 포함하지 않습니다.

Project Amber와 TextMap 원본 데이터의 이용 조건은 공유/배포 전에 별도로 확인해야 합니다.
