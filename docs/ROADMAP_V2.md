# Roadmap v2

Updated: 2026-06-30

This document records the current interpretation of the roadmap after v0.8
Evidence Pin operationalization and v0.8.1 QA/search hardening. The canonical
execution order is in `docs/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md`; this file
summarizes the product direction and remaining gaps.

## Current Stage

The current system is a developer-facing retrieval core:

- Project Amber v2 corpus/search DB.
- Deterministic `basic_lookup` QA for supported entities.
- AnswerPlan route metadata.
- Local LLM rewriter and semantic parser support.
- ConversationState v0.1.
- Source Reader v0.1.
- Evidence Pack prototype.
- Evidence Pin store and CLI workflow.
- `search` and `investigate` as the current lore exploration path.

It is not yet:

- A full summary/analysis/research writer.
- An autonomous research agent.
- A production API or web UI.
- A vector/motif/graph retrieval system.
- A long-term memory product.

## Direction Change

The next bottleneck is not raw answer speed. The bottleneck is query meaning.

The project should understand a user query by inspecting DB-grounded candidates
before final routing. This is documented in
`docs/DB_GROUNDED_QUERY_UNDERSTANDING.md`.

Core rules:

- Do not optimize primarily for speed.
- A slow conservative answer is better than a fast wrong answer.
- Strengthen LLM-based intent understanding, but validate it against DB/entity
  resolver output and Source Reader evidence.
- Keep supported exact lookup strict.
- Do not promote lore concepts into avatar/weapon/reliquary `basic_lookup`
  through weak partial overlap.
- Use previous conversation context only for genuinely low-information
  follow-ups.
- Do not let `last_entity` hijack explicit new topics.

## Capability Status

| Area | Current status | Notes |
| --- | --- | --- |
| Project Amber v2 DB | Implemented | Searchable official-data corpus exists. |
| `basic_lookup` QA | Implemented | Structured supported targets only. |
| Local LLM | Implemented as support | Rewriter/semantic parser; not fact authority. |
| Source Reader | Implemented | Unit/window/document/section/parallel text workflow. |
| Evidence Pin | Implemented | JSONL store, pin/list/show CLI, investigate integration. |
| Search/investigate | Implemented | Current lore exploration path. |
| DB-Grounded Query Understanding | Planned v0.8.3 | Candidate Meaning Pack and meaning-first routing. |
| Summary writer | Planned v0.9+ | Route metadata may exist, writer does not. |
| Analysis writer | Planned v0.9+ | Claim/evidence writer not implemented. |
| Research writer/loop | Future | Not an autonomous research agent yet. |
| API/Web UI/Memory | Future | Blocked behind stable core behavior. |

## v0.8.x Stabilization

v0.8.1 - Active QA/Search Bug Bash and current-scope hardening:

- Completed before this alignment pass.
- Hardened ambiguous QA/search routing and context handling.
- Added regressions around lore terms, explicit topics, and supported lookup.

v0.8.2 - Direction/Roadmap Alignment:

- Current documentation work.
- Adds canonical DB-grounded query understanding direction.
- Blocks v0.9 writers until v0.8.3 and v0.8.4 are complete.

v0.8.3 - DB-Grounded Query Understanding / Meaning Search:

- Build Candidate Meaning Pack.
- Add strong/weak/unsafe match policy.
- Use LLM semantic adjudication only over DB-backed candidates.
- Route unsupported lore concepts to search/investigate or conservative
  future-route behavior instead of wrong `basic_lookup`.

v0.8.4 - Regression Cleanup:

- Re-run QA/search bug bash.
- Expand evaluation cases.
- Correct route/status metadata.
- Confirm docs and implementation claims match.

## v0.9 Writer Gate

v0.9 Summary/Analysis/Research Writer work is blocked until:

- v0.8.3 query understanding is implemented and tested.
- v0.8.4 cleanup passes.
- Source-readable results are available for lore concept candidates.
- Future-route behavior is conservative when a writer is not implemented.

The first v0.9 writer target can still be Summary V1, but it must be designed
as part of the broader evidence-grounded writer stack rather than a standalone
fast summarizer.

## Do Not Start Yet

- Vector search or vector DB as the main fix for query understanding.
- Motif graph.
- API/backend/frontend integration.
- Autonomous research agent.
- Summary/analysis/research answer generation before v0.8.x is done.

## Next Decision

v0.8.3 can begin when this documentation alignment is committed and pushed.
The implementation goal should be scoped to DB-Grounded Query Understanding /
Meaning Search only.
