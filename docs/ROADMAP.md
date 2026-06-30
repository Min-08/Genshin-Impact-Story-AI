# Roadmap

This is the high-level product roadmap. The execution-level checklist for Codex
work is `docs/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md`.

## Current Position

The project is a developer-facing retrieval and QA core for official Genshin
Impact lore data. It is not yet an API product, web UI, autonomous research
agent, or full ChatGPT-like assistant.

Implemented through v0.8:

- Project Amber v2 data pipeline and searchable SQLite assets.
- Deterministic `basic_lookup` QA for supported structured targets.
- Local LLM rewrite/semantic parser support with validator fallback.
- Search and `investigate` developer workflows.
- Source Reader CLI for units, windows, sections, documents, and parallel text.
- Evidence Pin storage and CLI operations.
- Evidence candidates and pinned evidence in `investigate()` output.

Fixed in v0.8.1:

- Current-scope QA/search hardening after the Evidence Pin work.
- Ambiguous lore-term regressions that could route to the wrong structured
  entity.
- Conservative conversation-context inheritance for explicit new topics.

Current documentation phase:

- v0.8.2 Direction/Roadmap Alignment.
- Canonical direction: `docs/DB_GROUNDED_QUERY_UNDERSTANDING.md`.

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
| v0.8.2 | Direction/Roadmap Alignment | Current | Align docs around DB-grounded query understanding before implementation. |
| v0.8.3 | DB-Grounded Query Understanding / Meaning Search | Next | Build Candidate Meaning Pack, strong/weak/unsafe matching, and meaning-first routing. |
| v0.8.4 | Regression Cleanup | Planned | Re-run bug bash and stabilize route/status metadata after v0.8.3. |
| v0.9 | Summary/Analysis/Research Writer Foundation | Blocked | Start writer work only after v0.8.x stabilization and query understanding complete. |
| v1.0 | Research Assistant MVP | Future | API, conversation orchestration, source viewer, workspace memory, and user-facing flow. |

## v0.8.3 Requirements

v0.8.3 should not implement v0.9 writers, vector search, motif graph, API, or
frontend integration. It should focus on query meaning:

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
- Search/investigate remains the current lore exploration path for concepts.
- Summary/analysis/research routes that lack writers still return conservative
  future-route behavior.
- Documentation no longer claims planned writers are implemented.

## Deferred Work

These are intentionally deferred until the grounded retrieval and query
understanding path is stable:

- Vector database or vector reranking as a primary retrieval dependency.
- Motif graph or graph search.
- Translation-diff, similar-passage, and co-occurrence expansion beyond the
  current source-readable search path.
- API backend and web/frontend product integration.
- Autonomous multi-agent research loop.
- Long-term workspace memory product.
