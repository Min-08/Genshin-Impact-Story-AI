# 라우팅 및 QA 문제 기록

이 문서는 대화형 QA에서 발견된 라우팅/대상 해석 문제를 임시로 모아두기 위한 기록이다.

## 1. 캐릭터 단독 질의가 analysis로 라우팅됨

### 현상

다음처럼 캐릭터 이름만 입력하거나 자연어로 기본 정보를 묻는 경우에도 상태줄의 route가 `analysis:0.55`로 표시된다.

```text
질문> 아야카에 대해서 알려줘
[route=analysis:0.55 | intent=character_basic_info | llm=used]

질문> 아야카
[route=analysis:0.55 | intent=character_basic_info | llm=used]
```

### 확인 결과

현재 라우터 기준 출력:

```text
아야카에 대해서 알려줘 -> route=analysis:0.55, signals=["default:analysis"]
아야카 -> route=analysis:0.55, signals=["default:analysis"]
아야카 정보 -> route=basic_lookup:0.82, signals=["game_info:정보"]
아야카 기본정보 -> route=basic_lookup:0.82, signals=["game_info:기본정보", "game_info:정보"]
```

QA 결과는 별도로 캐릭터를 찾아 `intent=character_basic_info`를 만든다. 즉, 답변 내용은 정형 기본정보인데 라우팅 표시는 `analysis`가 된다.

### 원인

`src/genshin_lore_db/search_engine/router.py`의 `route_query()`는 `정보`, `기본정보`, `캐릭터`, `무기`, `성유물` 같은 명시적 키워드가 있을 때만 `basic_lookup`으로 보낸다.

캐릭터 이름만 있거나 `~에 대해서 알려줘`처럼 일반적인 질의 표현만 있는 경우에는 `GAME_INFO_TERMS`에 걸리지 않아 마지막 default branch인 `analysis:0.55`로 떨어진다.

반면 `src/genshin_lore_db/search_engine/qa.py`의 `answer_question()`은 라우터와 독립적으로 `resolve_qa_target()`을 실행해 캐릭터 대상을 찾는다.

### 판단

현재 코드 기준으로는 의도된 fallback 동작이지만, 제품 동작으로는 부자연스럽다.

`intent=character_basic_info`로 정형 QA가 성공한 경우에는 route도 `basic_lookup`이 되는 편이 일관적이다.

### 수정 후보

- 라우터가 캐릭터/무기/성유물 alias 또는 제목 후보를 참조해 단독 엔티티 질의를 `basic_lookup`으로 분류한다.
- 또는 terminal/answer layer에서 QA facts가 `character_basic_info`, `weapon_basic_info`, `reliquary_effect_lookup`으로 확정되면 route를 `basic_lookup`으로 보정한다.
- `알려줘`, `대해서 알려줘`, `뭐야` 같은 일반 기본정보 질의 표현을 별도 signal로 추가한다.
- 라우터와 QA resolver가 서로 다른 판단을 내릴 때 status line에 mismatch를 기록하거나 테스트로 고정한다.

## 2. 일반 인사말이 캐릭터 기본정보로 답변됨

### 현상

```text
질문> 안녕
[route=analysis:0.55 | intent=character_basic_info | llm=used]
말라니는 5성 캐릭터입니다.
...
```

### 확인 결과

`resolve_qa_target()` 결과:

```text
안녕 -> project_amber:avatar:10000102 / title=말라니 / content_type=avatar
```

검색 fallback 결과의 상위 hit는 말라니 quotes의 다음 문장이다.

```text
안녕? 다른 팀원들도 안녕?
```

이후 해당 canonical_id가 말라니 캐릭터로 해석되어 `character_basic_info` 답변이 생성된다.

### 원인

`qa.py`의 `resolve_qa_target()`은 제목 기반 score가 없으면 `search_project_amber_v2()` fallback을 실행한다.

이 fallback이 캐릭터 대사 문서까지 검색하고, 대사에 포함된 `안녕`이 매칭된 뒤 canonical_id를 캐릭터 기본정보 대상으로 변환한다.

### 판단

이 동작은 버그에 가깝다. 인사말이나 너무 짧은 일반 발화는 정형 QA 대상 해석으로 들어가면 안 된다.

### 수정 후보

- `안녕`, `안녕하세요`, `ㅎㅇ`, `하이` 같은 인사말은 terminal/chat layer에서 별도 small talk intent로 처리한다.
- `resolve_qa_target()` fallback 전에 최소 질의 길이, 엔티티 힌트, content type hint를 검사한다.
- 정형 QA fallback 검색에서는 `avatar_quotes` 같은 대사 문서를 제외하거나, title/localization 매칭보다 낮은 신뢰도의 text hit는 바로 캐릭터 기본정보로 승격하지 않는다.
- fallback hit를 canonical_id로 바꾸기 전에 hit의 `document_kind`, `title`, `metadata.section`을 검사한다.

## 3. route와 intent가 독립 실행되어 불일치 가능

### 현상

터미널 출력의 `route`는 `terminal.py`에서 `route_query()` 결과를 붙인 값이고, `intent`는 `qa.py`에서 facts를 만든 뒤 정해지는 값이다.

```text
route=analysis:0.55 | intent=character_basic_info
```

### 원인

`src/genshin_lore_db/search_engine/terminal.py`:

```python
route = route_query(query).to_dict() if use_routing else None
result = answer_question(root, query, use_llm=use_llm, model=model)
```

현재 route는 answer execution plan으로 쓰이지 않고, 표시용 metadata에 가깝다.

### 수정 후보

- route를 먼저 결정한 뒤 answer layer가 해당 route에 맞는 resolver/writer를 실행하게 만든다.
- 또는 QA 결과가 정형 intent로 확정되면 route metadata를 재평가한다.
- 테스트에 route/intent 일관성 케이스를 추가한다.

## 관련 테스트 상태

현재 확인 시점에서 다음 테스트는 통과했다.

```text
tests/test_router.py
tests/test_terminal.py

4 passed
```

다만 현재 테스트는 `아야카`, `아야카에 대해서 알려줘`, `안녕` 케이스를 검증하지 않는다.
