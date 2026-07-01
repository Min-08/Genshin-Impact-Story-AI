# Roadmap

Status: canonical current roadmap and version gate.

This is the high-level product roadmap. The execution-level checklist for Codex
work is `docs/implementation/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md`.
See `docs/README.md` for the full documentation map.

## Current Position

The project is a developer-facing retrieval and QA core for official Genshin
Impact lore data. It is not yet an API product, web UI, autonomous research
agent, or full ChatGPT-like assistant.

Implemented through v0.8.4:

- Project Amber v2 data pipeline and searchable SQLite assets.
- Deterministic `basic_lookup` QA for supported structured targets.
- Local LLM rewrite/semantic parser support with validator fallback.
- Search and `investigate` developer workflows.
- Source Reader CLI for units, windows, sections, documents, and parallel text.
- Evidence Pin storage and CLI operations.
- Evidence candidates and pinned evidence in `investigate()` output.
- DB-Grounded Query Understanding / Meaning Search.
- v0.8.4 regression cleanup after the v0.8.3 implementation.

Fixed in v0.8.1:

- Current-scope QA/search hardening after the Evidence Pin work.
- Ambiguous lore-term regressions that could route to the wrong structured
  entity.
- Conservative conversation-context inheritance for explicit new topics.

Current planning status:

- Documentation map / naming cleanup is complete.
- v0.8.5 Claude-Code Lessons Architecture Alignment is documented in
  `docs/design/`.
- Next goal: v0.8.6 Minimal Runtime + Context Foundation.
- PM-approved direction:
  `docs/PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md`.

## Product Principle

Do not optimize primarily for answer speed. The product should act like a
deliberate lore research assistant. A slow conservative answer is better than a
fast wrong answer.

Query meaning should be inferred through DB-grounded candidate search before
final routing. LLM-based intent understanding is important and should be
strengthened, but LLM output must be validated by deterministic DB/entity
resolution and Source Reader evidence.

## Version Path

| Version | Name | Status | Goal |
| --- | --- | --- | --- |
| v0.6.x | QA Core Stabilization | Done | Deterministic route/QA contract, hard guards, style control, conversation state. |
| v0.7 | Source Reader Operationalization | Done | Search results can open source windows, documents, sections, and parallel text. |
| v0.8 | Evidence Pin Operationalization | Done | Evidence can be pinned, stored, listed, shown, and surfaced in investigate output. |
| v0.8.1 | Active QA/Search Bug Bash | Done | Harden current-scope QA/search behavior and ambiguous routing regressions. |
| v0.8.2 | Direction/Roadmap Alignment | Done | Align docs around DB-grounded query understanding before implementation. |
| v0.8.3 | DB-Grounded Query Understanding / Meaning Search | Done | Build Candidate Meaning Pack, strong/weak/unsafe matching, and meaning-first routing. |
| v0.8.4 | Regression Cleanup | Done | Re-run bug bash and stabilize route/status metadata after v0.8.3. |
| D-Docs | Documentation Map / Naming Cleanup | Done | Clarify canonical docs, planning docs, implementation records, and stale status labels. |
| v0.8.5 | Claude-Code Lessons Architecture Alignment | Done | Convert approved lessons into architecture contracts without implementing writers. |
| v0.8.6 | Minimal Runtime + Context Foundation | Next | Add minimal LLM profile, TurnContext, and PromptPackage contracts before writer work. |
| Final v0.8.x Audit | Writer Readiness Gate | Planned | Decide whether v0.9 starts with Summary V1 only or Summary + Analysis foundation. |
| v0.9 | Summary/Analysis/Research Writer Foundation | Blocked | Start writer work only after v0.8.5, v0.8.6, and the final v0.8.x audit. |
| v0.10 | Tool Engine / Execution Plan | Future | Add deterministic tool contracts before agentic loops. |
| v0.11 | Research Planner / Evidence Judge | Future | Add planner, evidence judge, gap analyzer, and stop controller. |
| v0.12 | Agentic Research Loop V1 | Future | Add bounded repeated research loop over approved tools. |
| v0.13 | Streaming / Visible Thinking Event Contract | Future | Add user-facing progress/status events, not private chain-of-thought exposure. |
| v1.0 | Research Assistant MVP | Future | API, conversation orchestration, source viewer, workspace memory, and user-facing flow. |

## v0.8.5 Architecture Alignment Outputs

v0.8.5 is a documentation-first architecture pass. It does not implement
runtime features. It defines the contracts v0.8.6 and later stages should
follow:

- `docs/design/LLM_RUNTIME_PROFILES.md`
- `docs/design/CONTEXT_ASSEMBLY_DESIGN.md`
- `docs/design/AGENTIC_LOOP_DESIGN.md`
- `docs/design/RESEARCH_LOOP_DESIGN.md`
- `docs/design/STREAMING_VISIBLE_THINKING_DESIGN.md`
- `docs/design/WRITER_FOUNDATION_DESIGN.md`

## v0.8.6 Planned Scope

v0.8.6 should implement minimal runtime/context foundations:

- LLM profile config files and loader.
- Runtime profile / provider config / runtime selector objects.
- TurnContext dataclass/schema.
- PromptPackage builder.
- Context assembler and policy blocks.
- Debug commands for context and prompt package inspection.
- Tests for profile loading, fallback, schema validation, context inheritance,
  and future-route policy.

v0.8.6 should not implement summary/analysis/research writers, agent loop,
research loop, streaming UI, API/backend integration, vector search, motif
graph, or workspace memory.

## v0.8.3 Implemented Scope

v0.8.3 does not implement v0.9 writers, vector search, motif graph, API, or
frontend integration. It focuses on query meaning:

- Search/inspect the DB before final routing.
- Build an inspectable Candidate Meaning Pack.
- Keep exact supported `basic_lookup` strict.
- Keep lore concepts out of avatar/weapon/reliquary `basic_lookup` unless the
  match is a safe supported-entity match.
- Use prior conversation context only for low-information follow-ups.
- Reject stale `last_entity` context when the user asks an explicit new topic.
- Use the LLM as semantic adjudicator, not final fact authority.
- Validate LLM-selected meanings against DB candidates and source-readable
  Search/Source Reader handles.

## v0.9 Prerequisites

v0.9 must not start until:

- v0.8.3 DB-Grounded Query Understanding is implemented and tested.
- v0.8.4 regression cleanup is complete.
- v0.8.5 architecture alignment is complete.
- v0.8.6 minimal runtime/context foundation is complete.
- The final v0.8.x audit says writer work can start.
- Search/investigate remains the current lore exploration path for concepts.
- Summary/analysis/research routes that lack writers still return conservative
  future-route behavior.
- Documentation no longer claims planned writers are implemented.
- v0.8.5 design docs remain consistent with the implementation scope selected
  for v0.8.6.

## Deferred Work

These are intentionally deferred until the grounded retrieval and query
understanding path is stable:

- Vector database or vector reranking as a primary retrieval dependency.
- Motif graph or graph search.
- Translation-diff, similar-passage, and co-occurrence expansion beyond the
  current source-readable search path.
- API backend and web/frontend product integration.
- Autonomous multi-agent research loop.
- Tool Engine, Research Planner, Evidence Judge, Stop Controller, and visible
  progress event streaming until their staged versions.
- Long-term workspace memory product.
