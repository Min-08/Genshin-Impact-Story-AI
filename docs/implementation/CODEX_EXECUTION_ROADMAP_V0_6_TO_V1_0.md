# CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0

Status: implementation record / execution checklist. Current status and gates
are controlled by `docs/README.md` and `docs/ROADMAP.md`.

> **Purpose:** This roadmap is an execution plan for Codex.
> It is intentionally separate from `ROADMAP.md`, implementation notes, and vision/design documents.
> Those documents describe the product vision. This document describes the safest implementation order from the current repository state.

Current filename:

```text
docs/implementation/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md
```

Do not rename this file to `ROADMAP.md`.
That name is reserved for the canonical high-level project roadmap.

---

## 0. Current Situation

The project vision is valid: build a Genshin Impact story/lore research AI that can retrieve official data, read original source text, cite evidence, compare hypotheses, and eventually answer like a grounded research assistant.

However, the implementation must not jump directly into a full research agent.

The current practical implementation center is:

1. **`basic_lookup` QA**
   - Character, weapon, and reliquary/artifact-style official data.
   - Template/facts-based answer generation.
   - Optional local LLM rewrite with validation fallback.

2. **Search / investigate engine**
   - Hybrid retrieval.
   - Query expansion.
   - Evidence-pack-like result packaging.
   - Not yet a full answer generator.

3. **Source Reader**
   - Can read units, windows, sections, documents, and parallel language text.
   - This is the foundation for grounded summary, analysis, and research.

4. **Evidence Pin workflow**
   - Evidence pins, JSONL storage, pin/list/show CLI behavior, and
     `investigate()` candidate/pinned evidence output are operational at v0.8.

5. **DB-Grounded Query Understanding**
   - Implemented in v0.8.3.
   - Query meaning is inferred from DB-backed candidates before final
     routing.
   - This is required before summary/analysis/research writer work begins.

The main implementation risk is scope explosion:
- Do not build vector search too early.
- Do not build graph search too early.
- Do not build frontend before the backend flow is stable.
- Do not build a free-form agent before source reading and evidence validation are reliable.

---

## 1. Global Implementation Rules for Codex

### 1.1 Scope Freeze Rules

Until v0.12 is complete, do **not** implement:

- Full autonomous research agent
- Graph database
- Large motif ontology
- Vector database server
- Web frontend
- Workspace UI
- Multi-provider LLM abstraction layer
- Complex agentic tool-calling framework
- External project import or OpenWebUI-style grafting
- Long-term memory beyond the specified workspace JSON/JSONL stage

These are not rejected features. They are deferred.

### 1.2 Allowed Work Before v0.12

Allowed:

- Hardening `basic_lookup`
- Strengthening validators
- Connecting search results to source windows
- Adding CLI commands for source reading
- Adding evidence storage and evidence viewing
- Implementing DB-Grounded Query Understanding / Meaning Search
- Implementing summary route after v0.8.x stabilization
- Implementing grounded answer orchestration
- Implementing analysis route
- Implementing research v1 after the evidence pipeline exists

### 1.3 Development Principle

Every feature must follow this sequence:

```text
deterministic data flow
→ source visibility
→ evidence representation
→ LLM generation
→ validation
→ tests
```

Never place LLM generation before source visibility and validation.

Do not optimize primarily for answer speed. A slow conservative answer is
better than a fast wrong answer. The system should inspect DB candidates and
source-readable evidence before it commits to a route, especially for lore
concepts and ambiguous short queries.

### 1.4 Required Completion Standard

A version is not complete until:

- It has tests.
- It has a deterministic fallback when LLM fails.
- It does not break existing `basic_lookup`.
- It has clear unsupported behavior for out-of-scope questions.
- It returns debug data sufficient to diagnose routing/retrieval/validation failures.

---

# Version Roadmap

---

# v0.6.x — Stabilize Current QA Core

## Goal

Stabilize the currently working vertical slice:

```text
user question
→ route
→ exact/basic lookup
→ structured facts
→ draft answer
→ optional LLM rewrite
→ validator
→ final answer
```

This version must not add large new architecture.

---

## v0.6.1 — Baseline Audit and Lock

### Objective

Establish a stable baseline for current behavior.

### Tasks

1. Audit these files and flows:
   - `src/genshin_lore_db/search_engine/qa.py`
   - `src/genshin_lore_db/search_engine/router.py`
   - `src/genshin_lore_db/search_engine/semantic.py`
   - `src/genshin_lore_db/search_engine/local_llm.py`
   - Existing tests under `tests/`

2. Record current supported content types:
   - `avatar`
   - `weapon`
   - `reliquary`

3. Verify that `answer_question(..., use_llm=False)` works for all core supported cases.

4. Verify that `answer_question(..., use_llm=True)`:
   - Uses local LLM only as a limited rewrite step.
   - Falls back to draft answer if validation fails.
   - Does not hallucinate numbers or names.

5. Add or update tests for baseline behavior.

### Required Test Queries

```text
푸리나 알려줘
푸리나 기본정보
푸리나 별자리
푸리나 특성
아야카 알려줘
아야카 별자리
안개를 가르는 회광 정보
안개를 가르는 회광 제련별 효과
절연의 기치 효과
절연의 기치 파츠 알려줘
```

### Acceptance Criteria

- All above queries resolve to `basic_lookup`.
- Each result includes:
  - `final_answer`
  - `sources`
  - `route`
  - `canonical_id`
  - `content_type`
- LLM disabled mode passes.
- LLM enabled mode passes or safely falls back.
- No summary/research/vector/frontend work is added.

---

## v0.6.2 — Unsupported Guard Hardening

### Objective

Prevent unsupported gameplay/meta/strategy questions from being answered as official data.

### Unsupported Query Types

Block these as unsupported:

```text
추천
티어
세팅
파티
조합
메타
딜사이클
나선비경
공략
육성법
성능
```

### Tasks

1. Extend or verify `UNSUPPORTED_ANSWER_TERMS`.
2. Ensure deterministic hard guard runs before LLM semantic routing.
3. If LLM semantic parse says `basic_lookup` for an unsupported query, deterministic guard must still win.
4. Improve unsupported final answer:
   - It must explain that the current system only supports official data lookup/research.
   - It must not produce gameplay advice.
   - It may suggest asking for official data instead.

### Required Test Queries

```text
피슬 성유물 추천해줘
푸리나 세팅 알려줘
아야카 파티 추천
나선비경 티어 알려줘
무기 티어표 알려줘
현재 메타 알려줘
라이덴 딜사이클 알려줘
```

### Acceptance Criteria

- All queries above return `unsupported`.
- `unsupported_reason` is stable and machine-readable.
- No LLM answer generation is attempted for blocked categories.
- Regression tests cover deterministic guard priority.

---

## v0.6.3 — Follow-up Context Stabilization

### Objective

Make short follow-up questions resolve safely using active conversation context.

### Expected Conversation Flow

```text
User: 아야카 알려줘
Assistant: 아야카 기본정보 답변

User: 별자리
Assistant: 아야카 별자리 답변

User: 특성도
Assistant: 아야카 특성 답변

User: 근거는?
Assistant: 직전 답변의 출처/근거 표시
```

### Tasks

1. Audit `ConversationState`.
2. Ensure `active_entity` is updated after successful `basic_lookup`.
3. Ensure `last_sources` is updated after answers with sources.
4. Add follow-up resolution for:
   - `별자리`
   - `특성`
   - `제련`
   - `더 자세히`
   - `짧게`
   - `근거는?`
   - `출처는?`
   - `원문은?`

5. If no active entity exists, return clarification instead of guessing.

### Required Test Flows

```text
아야카 알려줘 → 별자리
아야카 알려줘 → 특성도
안개를 가르는 회광 알려줘 → 제련 효과는?
절연의 기치 알려줘 → 더 자세히
푸리나 알려줘 → 근거는?
별자리
근거는?
```

### Acceptance Criteria

- Follow-up queries use context only when context is available.
- Context-free intent-only queries ask for a specific entity.
- Evidence/source follow-ups route to source/evidence behavior.
- No wrong entity substitution.

---

## v0.6.4 — Validator Strengthening

### Objective

Make LLM rewrite safe enough to keep.

### Validator Must Reject

- New numbers not present in facts or draft.
- New percentages not present in facts or draft.
- New quoted names not present in facts or draft.
- Changed effect values.
- Missing required source fragments.
- Overlong rewritten answer.
- Repeated duplicated answer.
- Wrong type phrase, such as turning a weapon into an artifact.

### Tasks

1. Extend existing validator tests.
2. Ensure validator returns structured reasons.
3. Store validation debug in result.
4. Ensure failed LLM output is not used as final answer.
5. Ensure draft fallback is always valid.

### Acceptance Criteria

- Tests cover all rejection types.
- `llm.validation` appears in debug state when LLM is used.
- `final_answer` is never an invalid LLM rewrite.

---

## v0.6.x Done Definition

v0.6.x is complete when:

```text
basic_lookup stable
unsupported guard stable
follow-up context stable
validator stable
LLM fallback safe
tests pass
no new large architecture added
```

---

# v0.7 — Source Reader Operationalization

## Goal

Turn Source Reader from a backend primitive into an actual developer workflow.

Core flow:

```text
search result
→ source-readable id
→ read window
→ read document/section
→ read parallel text
```

---

## v0.7.1 — Search Result ID Standardization

### Objective

Every source-readable search result must include enough IDs to open original context.

### Required Result Fields

Where possible, search/investigate results must include:

```json
{
  "result_type": "unit_or_chunk",
  "unit_id": "...",
  "chunk_id": "...",
  "document_id": "...",
  "section_id": "...",
  "canonical_id": "...",
  "language": "ko",
  "title": "...",
  "text": "...",
  "ordinal": 0,
  "source_url": "...",
  "score": 0.0
}
```

### Tasks

1. Determine whether current v2 search results already contain `unit_id`.
2. If not, implement a mapping adapter:
   - `chunk_id` → `unit_id`, or
   - `document_id + ordinal` → `unit_id`.
3. Prefer Project Amber v2 DB as the canonical source-reader DB.
4. Add tests for mapping from top search results to readable windows.

### Acceptance Criteria

- Top search results can be passed into source reader.
- No manual DB lookup is needed by the user.
- Missing mapping is reported as structured error, not crash.

---

## v0.7.2 — `read-window` CLI

### Objective

Add a CLI command to read context around a unit.

### Command

```bash
python -m genshin_lore_db read-window <unit_id> --before 5 --after 5
```

### Optional Flags

```bash
--json
--before 10
--after 10
--language ko
```

### Human-readable Output

```text
Document: ...
Title: ...
Language: ko
Unit: ...

[Before]
...

[Center]
...

[After]
...
```

### Tasks

1. Connect CLI to `ProjectAmberV2SourceReader.read_window`.
2. Validate `unit_id`.
3. Support JSON output.
4. Support readable output.
5. Add tests for valid/invalid unit ids.

### Acceptance Criteria

- Valid unit opens surrounding context.
- Invalid unit returns clear error.
- JSON output is stable enough for later API/frontend.

---

## v0.7.3 — `read-document` and `read-section` CLI

### Commands

```bash
python -m genshin_lore_db read-document <document_id>
python -m genshin_lore_db read-section <section_id>
```

### Optional Flags

```bash
--json
--max-units 100
--no-units
```

### Tasks

1. Connect CLI to `read_document`.
2. Connect CLI to `read_section`.
3. Add pagination/limit for long documents.
4. Include metadata:
   - title
   - language
   - content_type
   - canonical_id
   - source_url
   - section count
   - unit count

### Acceptance Criteria

- Documents can be inspected without writing Python code.
- Long documents do not flood terminal by default.
- Output can feed into summary later.

---

## v0.7.4 — `read-parallel` CLI

### Command

```bash
python -m genshin_lore_db read-parallel <unit_id> --languages ko,en,ja,zh-Hans
```

### Tasks

1. Connect CLI to `read_parallel`.
2. Display language blocks in stable order.
3. Indicate missing languages.
4. Preserve unit ids for each language.

### Output Example

```text
[ko]
...

[en]
...

[ja]
...

[zh-Hans]
...
```

### Acceptance Criteria

- A Korean unit can show corresponding English/Japanese/Chinese text if present.
- Missing languages are explicit.
- This becomes the base for translation-note evidence.

---

## v0.7.5 — `search --with-window`

### Objective

Make search results immediately inspectable.

### Command

```bash
python -m genshin_lore_db search "천리 셀레스티아 관계" --limit 5 --with-window
```

### Tasks

1. Run search.
2. For each top result, resolve readable `unit_id`.
3. Attach `read_window(before=3, after=3)`.
4. Provide both JSON and human-readable output.

### Acceptance Criteria

- Top N results show text plus surrounding context.
- Result/window linkage is stable.
- This command is suitable for Codex debugging.

---

## v0.7 Done Definition

```text
search result can open source window
document/section can be read
parallel text can be read
CLI workflow works
tests pass
```

---

# v0.8 — Evidence Pin and Evidence Pack Operationalization

## Goal

Allow evidence to be selected, stored, listed, and reused.

---

## v0.8 Evidence Pin Step A - Evidence Store

### Storage

Use JSONL first, not SQLite.

```text
data/workspaces/default/evidence_pins.jsonl
```

### Evidence Record

```json
{
  "schema_version": "evidence_pin.v0.1",
  "evidence_id": "E-xxxxxxxxxxxx",
  "workspace_id": "default",
  "document_id": "...",
  "unit_id": "...",
  "section_id": "...",
  "canonical_id": "...",
  "language": "ko",
  "content_type": "...",
  "title": "...",
  "start_char": 0,
  "end_char": 42,
  "role": "supports",
  "source_level": "L0",
  "excerpt": "...",
  "hypothesis_ids": [],
  "note": "...",
  "created_at": "..."
}
```

### Tasks

1. Create evidence store module.
2. Implement append.
3. Implement list.
4. Implement lookup by `evidence_id`.
5. Prevent duplicate record if same evidence id already exists.
6. Support workspace id.

### Acceptance Criteria

- Evidence can be saved and reloaded.
- Duplicate evidence does not create uncontrolled duplicates.
- Evidence store is deterministic and testable.

---

## v0.8 Evidence Pin Step B - `pin-evidence` CLI

### Command

```bash
python -m genshin_lore_db pin-evidence \
  --unit-id <unit_id> \
  --start 10 \
  --end 80 \
  --role supports \
  --note "천리와 셀레스티아 관계 근거"
```

### Supported Roles

```text
supports
weakly_supports
context
counter
ambiguous
translation_note
```

### Tasks

1. Connect to `pin_unit_evidence`.
2. Validate start/end bounds.
3. Validate role.
4. Save to evidence store.
5. Print saved evidence id.

### Acceptance Criteria

- Unit substring can be pinned.
- Invalid ranges fail clearly.
- Invalid role fails clearly.
- Saved evidence can be listed.

---

## v0.8 Evidence Pin Step C - Evidence List / Show CLI

### Commands

```bash
python -m genshin_lore_db evidence list
python -m genshin_lore_db evidence show E-xxxxxxxxxxxx
python -m genshin_lore_db evidence list --role counter
python -m genshin_lore_db evidence list --query "셀레스티아"
```

### Tasks

1. Implement list by workspace.
2. Implement filter by role.
3. Implement text/title query filter.
4. Implement show by id.
5. Add JSON output.

### Acceptance Criteria

- Evidence can be browsed.
- Evidence can be inspected.
- Evidence can be filtered.

---

## v0.8 Evidence Pin Step D - Candidate Evidence in Investigate

### Objective

Investigate results should expose evidence candidates, even before manual pinning.

### Required Output Additions

```json
{
  "candidate_evidence": [
    {
      "unit_id": "...",
      "document_id": "...",
      "title": "...",
      "language": "ko",
      "excerpt": "...",
      "suggested_role": "context",
      "score": 0.0,
      "source_url": "..."
    }
  ],
  "pinned_evidence": [],
  "counter_candidates": [],
  "translation_note_candidates": []
}
```

### Tasks

1. Build candidate evidence from top hits/windows.
2. Do not use LLM to decide final evidence role yet.
3. Use simple rule-based `suggested_role`.
4. Include existing pinned evidence for same workspace/query if available.

### Acceptance Criteria

- `investigate()` output can be used to choose pins.
- Candidate evidence has unit/document ids.
- Candidate evidence is not treated as confirmed proof until pinned.

---

## v0.8 Done Definition

```text
evidence pins persist
evidence can be listed/shown
investigate returns evidence candidates
source_reader and evidence store are connected
tests pass
```

---

# v0.8.x - Stabilization Before Writer Work

This phase is required before v0.9. It exists because the system should not
start summary/analysis/research writers while query meaning is still routed by
brittle heuristics or weak entity overlap.

## v0.8.1 - Active QA/Search Bug Bash and Current-Scope Hardening

Status: completed before v0.8.2.

Scope:

1. Harden exact supported `basic_lookup` behavior.
2. Keep supported exact lookup strict.
3. Prevent lore concepts from being promoted to avatar/weapon/reliquary
   `basic_lookup` by weak partial overlap.
4. Keep previous conversation context only for genuinely low-information
   follow-ups.
5. Ensure explicit new topics are not hijacked by `last_entity`.
6. Add regression coverage for ambiguous lore terms, explicit story/topic
   requests, and supported entity lookups.

## v0.8.2 - Direction/Roadmap Alignment

Status: current documentation goal.

Scope:

1. Add `docs/DB_GROUNDED_QUERY_UNDERSTANDING.md`.
2. Align roadmap and search/QA docs with meaning-first routing.
3. State that speed is not the primary optimization target.
4. Make clear that LLM intent understanding should be strengthened, but LLM
   output must be validated by deterministic DB/entity resolution and Source
   Reader evidence.
5. Mark summary/analysis/research writers as future work until implementation
   exists.

## v0.8.3 - DB-Grounded Query Understanding / Meaning Search

Status: implemented in v0.8.3.

Scope:

1. Added a query-understanding layer before final routing.
2. Built Candidate Meaning Pack diagnostics from DB-backed candidates.
3. Classified candidate matches as strong, weak, or unsafe.
4. Use the LLM as a semantic adjudicator over DB candidates, not as a fact
   authority.
5. Validate LLM-selected meanings through deterministic DB/entity resolver and
   source-readable Search/Source Reader handles.
6. Route lore concepts to source-readable `search`/`investigate` behavior when
   no implemented structured writer exists.

Done definition:

```text
candidate meaning pack exists
strong/weak/unsafe policy is implemented
ambiguous lore concepts do not enter wrong basic_lookup
explicit new topics ignore stale last_entity context
low-information follow-ups can still inherit context
LLM semantic adjudication is validated against DB candidates
tests and evaluations pass
```

## v0.8.4 - Regression Cleanup

Status: current regression cleanup after v0.8.3.

Scope:

1. Run QA/search bug bash again against v0.8.3.
2. Fix route/status/intent mismatches introduced by meaning-first routing.
3. Expand evaluation cases for ambiguous terms and future-route behavior.
4. Correct docs that still imply unimplemented writers exist.
5. Keep v0.9 blocked until cleanup passes.

## v0.8.x Done Definition

```text
v0.8 Evidence Pin remains stable
v0.8.1 bug bash regressions remain fixed
v0.8.2 docs are aligned
v0.8.3 query understanding is implemented and tested
v0.8.4 regression cleanup is complete
summary/analysis/research writers are still correctly marked as future work
```

---

# v0.9 - Summary/Analysis/Research Writer Foundation

## Goal

Implement the first non-basic writer foundation only after v0.8.x stabilization
and DB-Grounded Query Understanding are complete.

The initial v0.9 writer target is still Summary V1, but it must be designed as
part of the broader summary/analysis/research writer stack. Current summary,
analysis, and research routes should remain conservative until their writers
and validators are actually implemented.

---

## v0.9 Entry Requirements

v0.9 must not start until:

1. v0.8.3 DB-Grounded Query Understanding / Meaning Search is implemented.
2. Candidate Meaning Pack diagnostics are available in route/search QA traces.
3. Strong/weak/unsafe match policy prevents weak lore overlap from entering
   structured `basic_lookup`.
4. Explicit new topics are protected from stale conversation context.
5. Source-readable search/investigate results are available for lore concepts.
6. v0.8.4 regression cleanup is complete.

---

## v0.9.1 — Summary Scope Definition

### Supported in V1

```text
character_story_summary
book_or_document_summary
quest_or_mission_summary
```

### Not Supported Yet

```text
entire Genshin world summary
entire nation history
all Celestia theories
all lore timeline
all version story summary
```

### Tasks

1. Define summary intents.
2. Add scope checks.
3. Unsupported broad summary should ask user to narrow the target.

### Acceptance Criteria

- Supported summary requests proceed.
- Too-broad summary requests do not generate unreliable huge summaries.

---

## v0.9.2 — Summary Target Resolver

### Example Queries

```text
푸리나 스토리 요약해줘
수선화 십자원 내용 정리해줘
일월 과거사 요약
카리베르트 퀘스트 줄거리
```

### Resolver Output

```json
{
  "summary_target": {
    "surface": "푸리나",
    "canonical_id": "...",
    "target_type": "character_story",
    "confidence": 0.92
  }
}
```

### Tasks

1. Resolve exact entities where possible.
2. Resolve document/book title where possible.
3. Resolve quest title where possible.
4. If target is ambiguous, request clarification.
5. If target is missing, request specific title/entity.

### Acceptance Criteria

- Clear targets resolve.
- Ambiguous targets do not guess.
- Resolver output becomes part of debug data.

---

## v0.9.3 — Summary Document Collector

### Flow

```text
summary_target
→ search related documents
→ rank documents
→ read document/section
→ build source blocks
```

### Source Block

```json
{
  "document_id": "...",
  "title": "...",
  "language": "ko",
  "content_type": "...",
  "units": [
    {
      "unit_id": "...",
      "ordinal": 0,
      "text": "..."
    }
  ]
}
```

### Tasks

1. Collect candidate documents from search.
2. Read document or section.
3. Limit long sources.
4. Preserve source metadata.
5. Build source blocks for answer generation.

### Acceptance Criteria

- Summary has source blocks.
- Source blocks are inspectable.
- Source blocks are not too large for local LLM.

---

## v0.9.4 — Extractive Summary Fallback

### Objective

Provide a deterministic fallback before LLM generation.

### Tasks

1. Extract key sentences from source blocks.
2. Score by:
   - query term match
   - title match
   - entity name match
   - position in document
   - repeated proper nouns
3. Produce fallback summary:
   - key points
   - important names
   - source list

### Acceptance Criteria

- Summary route can return useful output even without LLM.
- Extractive fallback is source-grounded.
- LLM failure does not break summary.

---

## v0.9.5 — LLM Summary Generator

### Prompt Rules

The LLM must receive only source blocks and strict instructions:

```text
You are a Genshin Impact official-source summarizer.
Use only the provided SOURCE BLOCKS.
Do not invent facts.
Do not speculate.
If the source does not establish something, say it is not established by the provided source.
Separate confirmed summary from uncertainty.
```

### Output Format

```text
핵심 요약
사건 순서
중요한 고유명사
근거
확정 불가한 부분
```

### Tasks

1. Implement source-block prompt builder.
2. Generate Korean answer.
3. Include source references.
4. Store LLM debug state.
5. Validate output.

### Acceptance Criteria

- LLM summary uses only source blocks.
- It includes evidence/source section.
- It distinguishes confirmed facts from uncertainty.

---

## v0.9.6 — Summary Validator

### Must Reject

- New names absent from source blocks.
- New numbers absent from source blocks.
- Missing evidence/source section.
- Overconfident wording when source is ambiguous.
- Answer too long.
- Empty or malformed answer.

### Fallback

If rejected:

```text
use extractive summary fallback
```

### Acceptance Criteria

- Hallucinated summary is not final.
- Rejection reason is visible in debug.
- Extractive fallback is always available.

---

## v0.9 Done Definition

```text
supported summary route returns real answer
source blocks are used
LLM summary is validated
extractive fallback exists
tests pass
```

---

# v0.10 — Grounded Answer Orchestrator V1

## Goal

Unify the response pipeline across basic lookup, source reader, summary, and later analysis/research.

---

## v0.10.1 — Pipeline Result Schema

Every route should return a compatible result.

### Standard Result

```json
{
  "query": "...",
  "route": "summary",
  "intent": "...",
  "answer": "...",
  "sources": [],
  "evidence": [],
  "hypotheses": [],
  "warnings": [],
  "debug": {
    "route": {},
    "plan": {},
    "retrieval": {},
    "source_reader": {},
    "llm": {},
    "validator": {}
  }
}
```

### Tasks

1. Create standard result helper.
2. Wrap `basic_lookup` result into this shape without breaking existing fields.
3. Wrap `summary` result into this shape.
4. Wrap `source_reader` result into this shape.
5. Preserve backward compatibility where tests depend on existing keys.

### Acceptance Criteria

- New result schema is available.
- Existing tests still pass.
- Frontend/API can rely on stable fields later.

---

## v0.10.2 — Answer Plan Expansion

Existing `AnswerPlan` should become a real orchestrator input.

### Extended Answer Plan

```json
{
  "route": "summary",
  "intent": "character_story_summary",
  "entities": [],
  "requested_style": "default",
  "detail_level": "medium",
  "retrieval_plan": {
    "search_queries": [],
    "need_windows": true,
    "need_parallel": false,
    "max_sources": 8
  },
  "answer_policy": {
    "allow_inference": false,
    "require_evidence": true,
    "require_counter_evidence": false
  }
}
```

### Tasks

1. Extend answer plan data without breaking current normalization.
2. Add deterministic plan builder per route.
3. Store plan in debug.
4. Keep LLM semantic parse optional.

### Acceptance Criteria

- Each route has a plan.
- Plans are deterministic by default.
- LLM is not required to build a plan.

---

## v0.10.3 — Orchestrator Function

### Function

```python
answer_grounded_question(root, query, *, use_llm=True, conversation_state=None) -> dict
```

### Flow

```text
route
→ plan
→ retrieve
→ read sources
→ select evidence
→ generate answer
→ validate
→ return standard result
```

### Tasks

1. Implement orchestration without removing existing `answer_question`.
2. Internally call existing components.
3. Add route-specific handlers:
   - `basic_lookup`
   - `summary`
   - `source_reader`
   - `unsupported`
4. Do not implement analysis/research here yet.

### Acceptance Criteria

- Grounded orchestrator handles existing routes.
- Existing `answer_question` can delegate later.
- Debug data shows each stage.

---

## v0.10 Done Definition

```text
standard result schema exists
answer plan drives retrieval/generation
orchestrator handles basic/source/summary
tests pass
```

---

# v0.11 — Analysis V1

## Goal

Answer relationship/connection questions using multiple sources, while separating confirmed facts from interpretation.

---

## v0.11.1 — Analysis Query Classifier

### Supported Types

```text
entity_relation
concept_relation
symbol_relation
timeline_relation
identity_relation
```

### Example Queries

```text
천리와 셀레스티아 관계는?
푸리나와 포칼로스 관계 정리해줘
심연과 켄리아는 어떻게 연결돼?
세계수와 기억의 관계는?
```

### Tasks

1. Extract 2-4 target entities/concepts.
2. Identify relation type.
3. Refuse or clarify if target is too broad.
4. Route to analysis handler.

### Acceptance Criteria

- Relation questions no longer fall into unsupported by default.
- Missing/ambiguous entities trigger clarification.
- Analysis route does not claim research-level certainty.

---

## v0.11.2 — Multi-source Retrieval

### Retrieval Flow

```text
target A search
target B search
combined A+B search
shared document detection
shared concept/name detection
source window collection
```

### Tasks

1. Generate search queries per target.
2. Collect top windows for each target.
3. Collect combined query windows.
4. Deduplicate windows.
5. Rank by source quality and relevance.

### Acceptance Criteria

- Analysis uses multiple windows.
- Analysis does not rely on only one text hit.
- Retrieval debug lists search queries and selected windows.

---

## v0.11.3 — Evidence Role Classification

### Roles

```text
supports
weakly_supports
context
counter
ambiguous
translation_note
```

### Tasks

1. Assign simple rule-based role suggestions.
2. Identify direct co-mention as stronger than isolated mention.
3. Identify negation/contrast terms as possible counter or ambiguity.
4. Preserve role as suggested, not final proof.

### Acceptance Criteria

- Evidence candidates are role-grouped.
- Lack of counter-evidence is explicitly stated.
- Analysis does not overstate weak evidence.

---

## v0.11.4 — Analysis Answer Generator

### Required Format

```text
결론
확정 가능한 사실
연결 가능성
불확실한 부분
근거
```

### Prompt Policy

- Use only evidence blocks.
- Do not invent missing links.
- Do not say two entities are identical unless source explicitly says so.
- Use “가능성”, “해석 여지”, “확정 불가” when appropriate.

### Acceptance Criteria

- Answer separates fact and interpretation.
- Evidence is cited/listed.
- Validator rejects unsupported strong claims.

---

## v0.11 Done Definition

```text
relationship questions work
multi-source retrieval works
evidence roles exist
fact vs interpretation separation works
tests pass
```

---

# v0.12 — Research V1

## Goal

Implement the first version of the story hypothesis engine.

Research V1 is not a truth machine.
It is a hypothesis comparison engine.

---

## v0.12.1 — Hypothesis Object

### Schema

```json
{
  "hypothesis_id": "H-001",
  "claim": "...",
  "type": "identity|relation|succession|symbolic|timeline|causal",
  "status": "candidate",
  "supporting_evidence": [],
  "counter_evidence": [],
  "context_evidence": [],
  "translation_notes": [],
  "confidence": "low|medium|high",
  "weaknesses": [],
  "created_from_query": "..."
}
```

### Tasks

1. Create hypothesis data model.
2. Generate stable ids.
3. Add serialization.
4. Add tests.

### Acceptance Criteria

- Hypotheses can be created and serialized.
- IDs are stable enough for workspace use later.
- No workspace memory yet.

---

## v0.12.2 — Hypothesis Generator

### Example

Input:

```text
파네스와 천리는 같은 존재일 가능성이 있어?
```

Output:

```json
[
  {
    "claim": "파네스와 천리는 동일 존재일 가능성이 있다",
    "type": "identity"
  },
  {
    "claim": "파네스와 천리는 동일 존재가 아니라 같은 권능 계열일 가능성이 있다",
    "type": "relation"
  },
  {
    "claim": "천리는 파네스 이후 체제의 계승자일 가능성이 있다",
    "type": "succession"
  }
]
```

### Rules

- Generate at least 2 hypotheses for research questions.
- Do not generate only the user’s preferred theory.
- Include an alternative explanation when possible.
- Include a null/weak hypothesis when appropriate:
  - “The source does not support a strong connection.”

### Acceptance Criteria

- Research questions produce multiple hypotheses.
- Hypotheses are not final answers.
- Hypotheses can be independently searched.

---

## v0.12.3 — Hypothesis Evidence Search

### Flow

```text
hypothesis
→ supporting query generation
→ context query generation
→ counter query generation
→ source window reading
→ evidence grouping
```

### Tasks

1. Generate search queries for each hypothesis.
2. Search supports.
3. Search context.
4. Search counter evidence.
5. Read source windows for top hits.
6. Attach evidence candidates to hypothesis.

### Acceptance Criteria

- Each hypothesis gets evidence groups.
- Counter search is mandatory.
- If no counter found, record `counter_evidence_status = "not_found"`.

---

## v0.12.4 — Translation Difference Check

### Flow

```text
important evidence unit
→ read_parallel
→ compare ko/en/ja/zh-Hans
→ create translation_note candidate
```

### Tasks

1. Select important evidence units.
2. Read parallel text.
3. Detect obvious differences:
   - missing key term
   - different proper noun
   - stronger/weaker wording
4. Store as `translation_note`.

### Acceptance Criteria

- Research can show translation differences.
- Translation difference does not automatically prove a theory.
- It is presented as interpretive caution.

---

## v0.12.5 — Research Answer Generator

### Required Format

```text
요약 결론
가설 1
가설 2
가설 3
가장 강한 해석
부족한 근거
추가 확인 필요
```

### Required Behavior

- Must distinguish official fact from speculation.
- Must compare hypotheses.
- Must include counter evidence or state that counter evidence was not found.
- Must not claim certainty unless direct source text supports it.
- Must include confidence as low/medium/high, not exact percentages.

### Acceptance Criteria

- Research questions return hypothesis comparison.
- Answer includes supports/counters/translation notes where available.
- Validator rejects overconfident unsupported claims.
- Tests cover at least 10 research questions.

---

## v0.12 Done Definition

```text
research route works
hypotheses generated
evidence searched per hypothesis
counter search mandatory
translation notes possible
answer compares theories
tests pass
```

---

# v0.13 — Motif / Concept Index V1

## Goal

Allow the system to discover adjacent lore concepts that the user did not explicitly mention.

---

## v0.13.1 — Manual Concept Seed

### Initial Concepts

```text
달
태양
별
하늘
왕좌
운명
이름
기억
꿈
시간
세계수
심연
용
물
거울
인형
연극
재판
순환
금단 지식
강림자
신좌
```

### Concept Schema

```json
{
  "concept_id": "motif:moon",
  "names": ["달", "월", "moon", "luna"],
  "type": "motif",
  "related": ["seelie", "celestia", "time"],
  "status": "manual_seed"
}
```

### Acceptance Criteria

- Manual seed file exists.
- Aliases normalize consistently.
- Concept lookup works.

---

## v0.13.2 — Co-occurrence Index

### Output

```json
{
  "document_id": "...",
  "concept_hits": ["motif:moon", "motif:time"],
  "cooccurrence": [
    ["motif:moon", "motif:time", 3]
  ]
}
```

### Tasks

1. Scan source units/documents for concept aliases.
2. Count per-document concept hits.
3. Count concept co-occurrence.
4. Store processed index.

### Acceptance Criteria

- Concept co-occurrence is available.
- Research can ask for related motifs.
- Automatically discovered links are marked as candidates.

---

## v0.13.3 — Research Expansion

### Behavior

When user asks:

```text
푸리나 운명
```

System may expand with:

```text
연극
재판
신좌
예언
물
인간성
```

### Rules

- Manual seed concepts are trusted.
- Automatically discovered concepts are candidates.
- Do not let motif expansion dominate exact source retrieval.
- Always verify with source windows.

### Acceptance Criteria

- Research retrieval recall improves.
- Related concepts appear in debug.
- Expansion is transparent.

---

# v0.14 — Vector Search V1

## Goal

Find semantically related text that lexical search misses.

Do not implement before v0.13 is stable.

---

## v0.14.1 — Embedding Pipeline

### Storage

```text
data/processed/vector/units.npy
data/processed/vector/metadata.jsonl
data/processed/vector/config.json
```

### Tasks

1. Embed source units.
2. Store metadata:
   - unit_id
   - document_id
   - title
   - language
   - content_type
   - content_hash
3. Support resume/rebuild.
4. Avoid recomputing unchanged units.

### Acceptance Criteria

- Embeddings can be generated locally.
- Metadata maps vector result to source reader.
- Rebuild is deterministic enough for testing.

---

## v0.14.2 — Vector Retriever

### Output

```json
{
  "unit_id": "...",
  "vector_score": 0.82,
  "text": "...",
  "title": "..."
}
```

### Tasks

1. Implement local vector search.
2. Start with simple numpy cosine or FAISS.
3. Return top_k.
4. Connect result to source window.

### Acceptance Criteria

- Vector search works standalone.
- Vector result can open source window.
- It does not replace lexical search.

---

## v0.14.3 — Hybrid Fusion

### Initial Formula

```text
final_score =
  lexical_score * 0.55
+ vector_score  * 0.30
+ entity_score  * 0.10
+ source_score  * 0.05
```

### Tasks

1. Normalize lexical/vector scores.
2. Deduplicate by unit/document.
3. Preserve channel debug:
   - lexical
   - vector
   - entity
   - source
4. Evaluate on search test set.

### Acceptance Criteria

- Hybrid search improves recall without breaking exact lookup.
- Vector-only hits are never used without source verification.
- Debug explains why a result ranked high.

---

# v0.15 — Workspace Memory V1

## Goal

Allow research sessions to persist and continue.

---

## v0.15.1 — Workspace State

### Storage

```text
data/workspaces/default/workspace_state.json
```

### Schema

```json
{
  "workspace_id": "default",
  "active_entities": [],
  "active_hypotheses": [],
  "pinned_evidence": [],
  "recent_questions": [],
  "discarded_hypotheses": [],
  "user_notes": []
}
```

### Acceptance Criteria

- Workspace state can be saved and loaded.
- Recent questions persist.
- Active hypotheses persist.
- Evidence pins link to workspace.

---

## v0.15.2 — Hypothesis Lifecycle

### States

```text
candidate
active
supported
weak
discarded
needs_more_evidence
```

### Commands

```bash
python -m genshin_lore_db hypothesis list
python -m genshin_lore_db hypothesis accept H-001
python -m genshin_lore_db hypothesis discard H-002
python -m genshin_lore_db hypothesis note H-001 "근거 약함"
```

### Acceptance Criteria

- Hypothesis state can change.
- Discarded hypotheses are not repeatedly promoted.
- User notes attach to hypothesis.

---

## v0.15.3 — Contextual Research Follow-up

### Examples

```text
아까 가설 2번 더 파봐
그 반례 원문 보여줘
이 근거 저장해줘
가설 1은 폐기해
```

### Acceptance Criteria

- Follow-up can resolve active hypothesis.
- Evidence/source requests use workspace context.
- The system asks clarification if context is missing.

---

# v0.16 — API Server V1

## Goal

Expose backend functions for frontend.

---

## Endpoints

```text
POST /api/chat
POST /api/search
POST /api/investigate
GET  /api/source/window
GET  /api/source/document
POST /api/evidence/pin
GET  /api/evidence
GET  /api/workspace
POST /api/workspace/hypothesis
```

### Response Shape

```json
{
  "answer": "...",
  "route": "research",
  "sources": [],
  "evidence": [],
  "hypotheses": [],
  "warnings": [],
  "debug": {}
}
```

### Tasks

1. Use FastAPI or a similarly lightweight server.
2. Keep API thin.
3. Do not move core logic into API handlers.
4. Add request/response models.
5. Add basic tests.

### Acceptance Criteria

- CLI is no longer required for basic app integration.
- Source windows can be requested by id.
- Evidence can be pinned through API.
- Chat endpoint returns standard result schema.

---

# v0.17 — Frontend Chat UI V1

## Goal

Build a ChatGPT-like interface for the already-working backend.

Do not start this before v0.16.

---

## Required Screens

```text
initial screen
chat input
streaming answer
source cards
source window panel
evidence highlights
hypothesis comparison cards
workspace sidebar
```

### Progress Stages

Frontend must reflect backend stages, not fake arbitrary progress:

```text
질문 분석 중
관련 원문 검색 중
원문 문맥 확인 중
근거 정리 중
번역 차이 확인 중
가설 비교 중
답변 작성 중
검증 중
```

### Tasks

1. Implement chat input/output.
2. Render standard result schema.
3. Render sources.
4. Source card click opens source window.
5. Render evidence highlight.
6. Render hypotheses as cards.
7. Add streaming later only after normal JSON works.

### Acceptance Criteria

- User can ask a question and see answer.
- User can click source and inspect original text.
- Research answer displays hypothesis comparison.
- Frontend does not invent progress state.

---

# v1.0 — First Complete Genshin Lore Research AI

## v1.0 Definition

v1.0 is reached when all of these work together:

```text
basic_lookup
source_reader
evidence pin
summary
grounded answer orchestrator
analysis
research hypothesis comparison
translation notes
motif expansion
hybrid vector search
workspace memory
API
frontend
```

## v1.0 Example Supported Questions

```text
푸리나 알려줘
푸리나 스토리 요약해줘
푸리나와 포칼로스 관계 정리해줘
천리와 셀레스티아 관계는?
파네스와 천리는 같은 존재일 가능성이 있어?
심연과 켄리아 관계를 가설별로 정리해줘
방금 말한 가설 2번 근거 원문 보여줘
그 반례도 찾아줘
이 근거는 저장해줘
```

## v1.0 Quality Standard

The system must:

- Never present speculation as fact.
- Always show source/evidence for lore claims.
- Separate official facts from interpretation.
- Compare hypotheses instead of forcing one conclusion.
- Preserve source windows for user inspection.
- Support follow-up research.
- Fail safely when evidence is insufficient.

---

# Recommended Codex Execution Batches

Use these as separate Codex sessions.
Do not ask Codex to do multiple major versions at once.

---

## Batch 1 — v0.6.x

```text
Implement only v0.6.x from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement source reader CLI, summary, research, vector search, API, or frontend.

Focus:
- baseline tests
- unsupported guard
- follow-up context
- validator hardening

Return:
- changed files
- test summary
- remaining gaps
```

---

## Batch 2 — v0.7

```text
Implement only v0.7 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement evidence store, summary, research, vector search, API, or frontend.

Focus:
- source-readable search result ids
- read-window CLI
- read-document CLI
- read-section CLI
- read-parallel CLI
- search --with-window

Return:
- changed files
- CLI examples
- test summary
- remaining gaps
```

---

## Batch 3 — v0.8

```text
Implement only v0.8 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement summary, research, vector search, API, or frontend.

Focus:
- evidence JSONL store
- pin-evidence CLI
- evidence list/show CLI
- investigate candidate evidence

Return:
- changed files
- CLI examples
- test summary
- remaining gaps
```

---

## Batch 3.5 - v0.8.x Stabilization

```text
Implement only the v0.8.x stabilization phase from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement summary, analysis, research writers, vector search, motif graph, API, or frontend.

Focus:
- v0.8.1 QA/search regression hardening
- v0.8.2 roadmap/docs alignment
- v0.8.3 DB-Grounded Query Understanding / Meaning Search
- v0.8.4 regression cleanup
- strict basic_lookup and conservative context inheritance

Return:
- changed files
- route/query-understanding diagnostics
- test summary
- remaining gaps before v0.9
```

---

## Batch 4 - v0.9

```text
Implement only v0.9 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md after v0.8.x stabilization is complete.

Do not implement vector search, motif graph, API, or frontend.

Focus:
- summary target resolver
- summary document collector
- source blocks
- extractive fallback
- LLM summary generator
- summary validator
- writer contracts that keep analysis/research future routes conservative

Return:
- changed files
- example summary outputs
- test summary
- remaining gaps
```

---

## Batch 5 — v0.10 to v0.11

```text
Implement v0.10 and v0.11 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement research, motif index, vector search, API, or frontend.

Focus:
- standard result schema
- answer plan expansion
- grounded answer orchestrator
- analysis route
- multi-source retrieval
- evidence role grouping
- analysis answer validator

Return:
- changed files
- example analysis outputs
- test summary
- remaining gaps
```

---

## Batch 6 — v0.12

```text
Implement only v0.12 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement motif index, vector search, API, or frontend.

Focus:
- hypothesis model
- hypothesis generator
- hypothesis evidence search
- mandatory counter evidence search
- translation difference check
- research answer generator
- research validator

Return:
- changed files
- example research outputs
- test summary
- remaining gaps
```

---

## Batch 7 — v0.13 to v0.15

```text
Implement v0.13 through v0.15 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Do not implement frontend yet.

Focus:
- manual motif/concept seed
- co-occurrence index
- research expansion
- vector search
- hybrid fusion
- workspace memory
- hypothesis lifecycle

Return:
- changed files
- index build instructions
- test summary
- remaining gaps
```

---

## Batch 8 — v0.16 to v0.17

```text
Implement v0.16 and v0.17 from CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md.

Focus:
- API server
- frontend integration
- source cards
- evidence highlights
- hypothesis cards
- backend-driven progress stages

Return:
- changed files
- run instructions
- test summary
- remaining gaps
```

---

# Final Warning for Codex

Do not optimize for the appearance of progress.

The correct order is:

```text
working retrieval
→ readable source
→ pinned evidence
→ grounded summary
→ grounded analysis
→ hypothesis research
→ expansion/vector/memory
→ API/frontend
```

If a feature cannot expose its source text and evidence, it is not complete.

If a generated answer cannot be validated, it must not become the final answer.
