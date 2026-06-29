# Preflight Audit Issues

작성일: 2026-06-29  
범위: v0.6.x 이후 로드맵 작업을 시작하기 전에, 현재 구현된 `basic_lookup`/route/result 일관성/한국어 출력/평가 커버리지에 직접 영향을 주는 이슈만 선별했다.

이 문서는 `docs/ROADMAP_V2.md`를 반복하지 않는다. 이미 로드맵에 있는 기능 계획은 여기서 "왜 지금 고치지 않았는지"와 "어느 버전에서 다시 봐야 하는지"만 기록한다.

## 1. Fixed in this preflight task

### 1.1 Lore term이 basic_lookup 엔티티 답변으로 승격됨

- Severity: P1
- Category: route safety, entity resolution
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `tests/test_qa.py`, `config/answer_evaluation_set.json`
- Observed behavior: `"운명의 베틀 알려줘"`가 여행자 기본정보로, `"니벨룽겐 알려줘"`가 느비예트 기본정보로 답할 수 있었다.
- Fix summary: `resolve_qa_target()`에서 title/canonical/alias exact 후보가 없을 때 `search_project_amber_v2()` 첫 hit를 basic lookup 해석으로 쓰던 fallback을 제거했다.
- Verification: 새 테스트 `test_lore_terms_do_not_promote_to_basic_lookup_entities`와 평가 케이스 `unsupported_loom_plain_lookup`, `unsupported_nibelung_plain_lookup`를 추가했다.

### 1.2 LLM semantic parser가 DB resolve 없이 basic_lookup route를 만들 수 있음

- Severity: P1
- Category: route/result consistency, LLM authority boundary
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `tests/test_qa.py`, `config/answer_evaluation_set.json`
- Observed behavior: `"파네스 알려줘"`가 지원 DB 엔티티로 resolve되지 않아도 semantic parse가 `route=basic_lookup`, `intent=character_basic_info`를 만들 수 있었다.
- Fix summary: LLM semantic parse의 `basic_lookup`은 deterministic DB resolver가 성공한 경우에만 채택한다. 실패하면 deterministic fallback route로 흘려 `analysis + route_not_implemented` 상태를 보존한다.
- Verification: 새 테스트 `test_llm_basic_lookup_without_db_resolution_is_not_authoritative`와 평가 케이스 `unsupported_phanes_plain_lookup`를 추가했다.

### 1.3 한국어 문장 종결/조사 조합 오류

- Severity: P2
- Category: answer formatting
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `tests/test_qa.py`, `config/answer_evaluation_set.json`
- Observed behavior: `증가할 수 있다입니다`, `과거 때문이다입니다`, `주인공라고`, `있다라고`, `법구을` 같은 문장이 생성됐다.
- Fix summary: 한글 받침 기반 조사 헬퍼와 이미 완성된 한국어 문장에 `입니다`를 덧붙이지 않는 `complete_korean_sentence()`를 추가했다.
- Verification: 새 테스트 `test_draft_answers_avoid_korean_sentence_and_particle_regressions`와 평가셋 forbidden fragments를 추가했다.

### 1.4 평가 커버리지 공백

- Severity: P2
- Category: evaluation
- Affected files: `tests/test_qa.py`, `config/answer_evaluation_set.json`
- Observed behavior: 위 세 가지 회귀가 실제 사용자 질의에서는 재현됐지만 단위 테스트와 answer evaluation이 막지 못했다.
- Fix summary: exact lookup false-positive, unresolved LLM semantic basic lookup, 한국어 formatting regression을 테스트와 평가셋에 추가했다.
- Verification: `python -m pytest tests/test_qa.py -q`, `python scripts/eval_answer_engine.py --fail-under`.

### 1.5 웹 UI mock source가 실제 근거처럼 보일 수 있음

- Severity: P3
- Category: product safety, frontend copy
- Affected files: `web/src/App.jsx`
- Observed behavior: 정적 UI 목업의 `Source`, `Evidence`, `검색 결과`가 실제 backend evidence처럼 보일 수 있었다.
- Fix summary: 출처/증거/검색 결과 라벨에 `Demo` 또는 `데모 목업` 표시를 추가했다.
- Verification: build 검증 대상. 실제 backend 연결은 이번 범위가 아니다.

## 2. Must fix before v0.6.x

현재 preflight 수정 후 v0.6.x 착수 전 차단 이슈는 남기지 않는다. 단, 다음 조건은 완료 기준으로 계속 유지한다.

- `basic_lookup`은 deterministic DB resolution이 성공한 경우에만 최종 답변을 생성한다.
- LLM semantic parser는 route 보조 신호일 뿐, unsupported entity를 supported entity로 승인할 수 없다.
- no-LLM answer evaluation과 관련 단위 테스트가 100% 통과해야 한다.
- 새 route를 구현하지 않은 경우 `route_not_implemented`가 route와 answer_plan에 일관되게 남아야 한다.

## 3. Deferred to v0.7

### 3.1 `근거는?`이 실제 source window/span이 아니라 metadata만 표시함

- Severity: P1
- Category: source reader, evidence grounding
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `src/genshin_lore_db/search_engine/conversation.py`, `scripts/lore_search_engine.py`, `docs/ROADMAP_V2.md`
- Observed behavior: follow-up `"근거는?"`은 직전 답변의 `raw_ref`, `source_url` metadata를 보여주지만 원문 window, section, span pin은 제공하지 않는다.
- Why it matters: 분석/연구 답변으로 넘어가면 "근거 있음"과 "원문 일부를 재확인 가능"은 다른 품질 조건이다.
- Recommended future fix: 검색 hit와 `last_sources`를 Source Reader window API에 연결하고 Evidence Pack에 pinned span을 저장한다.
- Target roadmap version: v0.7 Source Reader / Evidence Pack Integration.
- Reason not fixed now: 이번 preflight 범위는 현재 `basic_lookup` 안전성과 회귀 테스트에 한정했다. 원문 window/pin은 새 data contract와 평가셋이 필요하다.

### 3.2 Summary scope resolver와 ordered source unit이 없음

- Severity: P2
- Category: summary route, retrieval planning
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `docs/ROADMAP_V2.md`, `config/answer_evaluation_set.json`
- Observed behavior: `"수메르 마신임무 요약해줘"` 같은 질의는 `summary` route로 분류되지만 writer와 scope unit이 없어 unsupported로 끝난다.
- Why it matters: summary route가 route contract만 있고 실제 범위 확정이 없으면 사용자는 요약 기능이 구현된 것으로 오해할 수 있다.
- Recommended future fix: 책/퀘스트/캐릭터 스토리별 scope resolver, ordered source units, summary 전용 평가셋을 만든다.
- Target roadmap version: v0.7.5 Summary Scope와 Summary Index.
- Reason not fixed now: 새 writer 또는 source reader 통합은 preflight 금지 범위에 포함된다.

## 4. Deferred to v0.8

### 4.1 Analysis route writer가 없음

- Severity: P1
- Category: analysis writer, claim grounding
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `src/genshin_lore_db/search_engine/router.py`, `docs/ROADMAP_V2.md`
- Observed behavior: 관계/분석 질의는 `analysis + route_not_implemented`로 보존되지만, 공식 근거/간접 연결/해석/약점 구조의 답변은 생성하지 않는다.
- Why it matters: 사용자가 원하는 핵심 기능은 단순 lookup보다 분석 답변인데, 현재는 route 계약만 존재한다.
- Recommended future fix: claim model, evidence pin, source_level validator, 반례 표시 규칙을 포함한 analysis writer를 구현한다.
- Target roadmap version: v0.8 Analysis Writer.
- Reason not fixed now: 현재 task는 구현된 기능의 correctness 보정이 목적이며, 새 route writer 구현은 로드맵 작업이다.

### 4.2 Claim-level validator가 없음

- Severity: P1
- Category: validation, factual safety
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `src/genshin_lore_db/search_engine/answer_evaluation.py`
- Observed behavior: 현재 validator는 필수 fragment, 숫자, 이름, forbidden term 중심이다. 관계 방향, 단정/추측 구분, 조건 누락은 검증하지 않는다.
- Why it matters: analysis writer가 붙으면 숫자나 이름이 맞아도 의미가 틀린 답변이 통과할 수 있다.
- Recommended future fix: `allowed_claims`, `forbidden_claims`, `required_qualifiers`, evidence span presence를 평가하는 validator를 추가한다.
- Target roadmap version: v0.8 Analysis Writer와 함께 도입.
- Reason not fixed now: claim schema와 writer 출력 형식이 아직 없어서 validator만 먼저 구현하면 허위 안정감을 준다.

## 5. Deferred to v0.9

### 5.1 Research route writer와 research loop가 없음

- Severity: P1
- Category: research route, hypothesis management
- Affected files: `src/genshin_lore_db/search_engine/qa.py`, `docs/ROADMAP_V2.md`, `docs/research/*`
- Observed behavior: `"운명의 베틀 떡밥 정리해줘"` 같은 질의는 `research + route_not_implemented`로 남는다.
- Why it matters: 프로젝트의 최종 방향은 추측/반례/근거 분리를 돕는 연구 보조 도구지만, 현재는 해당 루프가 없다.
- Recommended future fix: planner, reader, discovery, counter, synthesizer를 처음에는 역할 함수로 구현하고 hypothesis state와 반례 후보를 분리한다.
- Target roadmap version: v0.9 Research Loop v1.
- Reason not fixed now: 이번 task에서 multi-step research agent, graph, vector, memory 구현은 명시적으로 제외됐다.

### 5.2 Vector/motif/graph/translation-diff 계층이 없음

- Severity: P2
- Category: retrieval depth
- Affected files: `src/genshin_lore_db/pipeline/*`, `src/genshin_lore_db/search_engine/*`, `docs/ROADMAP.md`, `docs/ROADMAP_V2.md`
- Observed behavior: 현재 검색은 SQLite/FTS, alias, concept seed 중심이다. 벡터 검색, motif index, graph search, translation diff index는 없다.
- Why it matters: 연구형 질의에서 표면어가 다른 반복 모티프, 번역 차이, 간접 연결, 반례 후보를 놓칠 수 있다.
- Recommended future fix: FTS 결과를 유지한 채 vector/motif/graph를 보조 retrieval layer로 추가하고 route별 평가셋을 만든다.
- Target roadmap version: v0.9 또는 v0.9.5 retrieval expansion.
- Reason not fixed now: 현재 `basic_lookup` preflight와 무관하고, 데이터 산출물/평가셋/성능 기준을 함께 설계해야 한다.

## 6. Deferred to v0.10+

### 6.1 Web UI는 static mock이며 backend와 연결되지 않음

- Severity: P2
- Category: frontend, product integration
- Affected files: `web/src/App.jsx`, `web/src/styles.css`, `docs/ROADMAP_V2.md`
- Observed behavior: UI는 정적 mock data를 렌더링한다. 검색, 답변, source reader, evidence pack backend와 연결되어 있지 않다.
- Why it matters: 사용자가 목업을 실제 연구/검색 결과로 오해하면 신뢰도 문제가 생긴다.
- Recommended future fix: API contract가 안정된 뒤 real search/answer/source endpoints에 연결하고 mock data는 fixture/demo mode로 격리한다.
- Target roadmap version: v0.10+ API/Web UI integration.
- Reason not fixed now: 이번 task에서는 mock label만 안전하게 추가했다. backend integration은 로드맵 후순위다.

### 6.2 API, streaming, conversation orchestrator가 없음

- Severity: P2
- Category: service architecture
- Affected files: `scripts/lore_chat.py`, `scripts/lore_search_engine.py`, future API modules
- Observed behavior: 현재 사용 경로는 CLI와 로컬 스크립트 중심이다. FastAPI/SSE/API-backed chat endpoint는 없다.
- Why it matters: 웹 UI, tool-calling agent, 장기 세션 상태를 안정적으로 붙일 수 없다.
- Recommended future fix: search/answer/source reader API, NDJSON 또는 SSE streaming, session-scoped conversation state를 API contract로 분리한다.
- Target roadmap version: v0.10+ service layer.
- Reason not fixed now: API 구현은 현재 correctness preflight의 범위를 벗어난다.

### 6.3 Workspace Memory가 없음

- Severity: P2
- Category: memory, research state
- Affected files: future memory modules, `docs/research/*`
- Observed behavior: 현재 `ConversationState`는 세션 한정 active entity/follow-up 처리만 한다. 장기 연구 메모리, hypothesis lifecycle, memory patch/event log는 없다.
- Why it matters: 장기 연구에서는 공식 사실, 사용자 가설, AI 추론, 반박된 가설이 섞일 위험이 있다.
- Recommended future fix: source type과 confidence가 분리된 workspace memory schema, patch/event log, accepted/rejected/needs_review 상태를 만든다.
- Target roadmap version: v0.10+ Workspace Memory.
- Reason not fixed now: memory는 research loop와 source grounding이 먼저 안정화된 뒤 붙여야 한다.

## 7. Backlog / repository hygiene

### 7.1 Ollama startup이 Windows app-only install을 충분히 처리하지 못할 수 있음

- Severity: P3
- Category: local runtime, developer UX
- Affected files: `scripts/lore_chat.py`, `lore_chat.ps1`, `lore_chat.cmd`, `src/genshin_lore_db/search_engine/local_llm.py`
- Observed behavior: Ollama가 CLI PATH가 아닌 Windows 앱 설치 형태일 때 startup/help 경로가 실패하거나 안내가 불명확할 수 있다.
- Why it matters: LLM rewrite/semantic parser 사용자가 초기 실행에서 막힐 수 있다.
- Recommended future fix: Windows 앱 설치 경로 감지, `ollama serve` 상태 확인, 실패 시 명확한 복구 안내를 추가한다.
- Target roadmap version: backlog, v0.6.x maintenance.
- Reason not fixed now: basic lookup correctness와 직접 관련이 없고, 현재 변경 중인 launcher 파일에 기존 수정이 있어 별도 maintenance task가 안전하다.

### 7.2 documentation/version/test-count drift

- Severity: P3
- Category: documentation hygiene
- Affected files: `README.md`, `docs/ROADMAP_V2.md`, `docs/issues/*`, `config/answer_evaluation_set.json`
- Observed behavior: 문서에는 과거 test count/case count가 남아 있고, 목표 파일에서 언급한 `docs/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md`는 현재 작업트리에 없다.
- Why it matters: 검증 상태를 판단할 때 문서와 실제 CI/로컬 결과가 어긋날 수 있다.
- Recommended future fix: release checklist에서 pytest/eval case count를 자동 생성하거나, 수치가 필요한 문서를 한곳으로 제한한다.
- Target roadmap version: backlog, each release closeout.
- Reason not fixed now: 이번 task의 필수 산출물은 새 preflight issue tracker이며 전체 문서 동기화는 범위 밖이다.

### 7.3 Eval set still has route-specific blind spots

- Severity: P2
- Category: evaluation coverage
- Affected files: `config/answer_evaluation_set.json`, `src/genshin_lore_db/search_engine/answer_evaluation.py`, future route-specific eval sets
- Observed behavior: 이번에 확인된 false positive는 추가했지만 summary/analysis/research writer, source span, claim validation 전용 평가는 아직 없다.
- Why it matters: route가 늘어날수록 global pass rate만으로는 품질이 보장되지 않는다.
- Recommended future fix: route별 fixture와 threshold를 분리하고, source span/claim-level metrics를 추가한다.
- Target roadmap version: backlog, feature별 gate.
- Reason not fixed now: 아직 해당 route writer와 source span contract가 없다.

### 7.4 Playwright logs, zip artifacts, copied web files, `.gitignore` patterns

- Severity: P3
- Category: repository hygiene
- Affected files: `.playwright-mcp/*.log`, `web/src/r-App.jsx`, `web/src/r-styles*.css`, possible archive artifacts, `.gitignore`
- Observed behavior: 현재 작업트리에 Playwright console logs와 복사본 형태의 untracked web files가 있다.
- Why it matters: 리뷰 노이즈가 커지고, 실제 소스와 임시 산출물을 혼동할 수 있다.
- Recommended future fix: 필요한 산출물만 보존하고, 반복 생성되는 로그/임시 파일은 `.gitignore`에 추가한다.
- Target roadmap version: backlog, before PR/commit.
- Reason not fixed now: 기존 사용자/이전 작업 변경일 수 있어 임의 삭제하지 않았다.

### 7.5 `amber_project_db_builder` copy가 root implementation과 drift할 수 있음

- Severity: P3
- Category: code organization
- Affected files: duplicated builder scripts/modules around Project Amber DB build path
- Observed behavior: root implementation과 별도 copy가 함께 존재하면 한쪽만 수정되어 검색 DB 산출물이 달라질 수 있다.
- Why it matters: 재빌드 재현성과 audit 결과 신뢰도가 떨어진다.
- Recommended future fix: 단일 canonical builder module로 합치거나 copy가 필요한 이유와 sync test를 문서화한다.
- Target roadmap version: backlog, pipeline maintenance.
- Reason not fixed now: 이번 preflight는 answer/runtime behavior만 수정했고 pipeline refactor는 제외됐다.

### 7.6 Web build가 `--emptyOutDir false`를 사용함

- Severity: P3
- Category: build hygiene
- Affected files: `web/package.json`, `web/dist/*`
- Observed behavior: build output directory를 비우지 않으면 오래된 asset이 남아 UI 검증이나 배포 산출물을 오염시킬 수 있다.
- Why it matters: 정적 목업과 실제 연결 이후 asset mismatch를 디버깅하기 어려워진다.
- Recommended future fix: build artifact 전략을 정하고, 필요한 경우 clean build script와 artifact ignore 정책을 추가한다.
- Target roadmap version: backlog, before web integration.
- Reason not fixed now: 현재 웹은 static mock이고, build script 정책 변경은 이번 correctness fix와 직접 관련이 없다.
