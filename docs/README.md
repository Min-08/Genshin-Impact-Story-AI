# Documentation Index

Status: canonical documentation map for the current repository.

This index separates current source-of-truth documents from implementation
records, planning notes, and issue logs. Use it before editing architecture,
roadmap, or route behavior docs.

## Current Status

The current implemented core is a developer-facing retrieval and QA system:

- v0.8.3 DB-Grounded Query Understanding is implemented.
- v0.8.4 regression cleanup has passed local verification.
- Documentation map / naming cleanup is complete in this docs pass.
- v0.8.5 Claude-Code Lessons Architecture Alignment is the next recommended
  goal.
- v0.8.6 Minimal Runtime + Context Foundation is planned before v0.9 writer
  work.

Summary, analysis, and research writers are not implemented yet. API, frontend
integration, vector search, motif graph, autonomous research loop, and
workspace memory remain future work unless a later roadmap document says
otherwise.

## Canonical Docs

| Document | Role |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | Current product roadmap and version gate. |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Current architecture and implementation status. |
| [DB_GROUNDED_QUERY_UNDERSTANDING.md](DB_GROUNDED_QUERY_UNDERSTANDING.md) | Canonical v0.8.3 query-understanding contract and implementation record. |
| [ANSWER_ROUTING_DESIGN.md](ANSWER_ROUTING_DESIGN.md) | Route contracts for `basic_lookup`, `summary`, `analysis`, and `research`. |
| [SEARCH_ENGINE.md](SEARCH_ENGINE.md) | Current search, investigate, Source Reader, and Evidence workflow reference. |

## Planning Sources

| Document | Role |
| --- | --- |
| [PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md](PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md) | PM-approved source of truth for v0.8.5, v0.8.6, and v0.9 sequencing. |
| [CLAUDE_CODE_LESSONS_APPLICATION_PLAN.md](CLAUDE_CODE_LESSONS_APPLICATION_PLAN.md) | Design input for v0.8.5+ architecture alignment. |
| [PROJECT_VISION.md](PROJECT_VISION.md) | Long-range product vision. Current roadmap and architecture docs control implementation status. |

## Reference Docs

| Document | Role |
| --- | --- |
| [DATA_PIPELINE.md](DATA_PIPELINE.md) | Data collection, processing, canonicalization, and generated artifact layout. |
| [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Repository layout and ownership guide. |
| [research/](research/) | Research notes and stage-decision context. |

## Implementation Records

These files are historical/execution records. They are useful context, but they
are not the first source of truth when they conflict with the canonical docs.

| Document | Role |
| --- | --- |
| [implementation/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md](implementation/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md) | Detailed Codex execution checklist from v0.6 through later staged work. |
| [implementation/ROADMAP_V2_IMPLEMENTATION_NOTES.md](implementation/ROADMAP_V2_IMPLEMENTATION_NOTES.md) | Earlier roadmap-v2 implementation notes and status snapshot. |

## Issues And Audits

| Document | Role |
| --- | --- |
| [issues/](issues/) | Issue notes and follow-up trackers. |
| [PREFLIGHT_AUDIT_ISSUES.md](PREFLIGHT_AUDIT_ISSUES.md) | Preflight audit log and deferred issue record. |

## Legacy Docs

There are no intentionally archived legacy docs at this time. If a future pass
finds a truly superseded document, move it under `docs/legacy/` with a short
status banner instead of deleting it.

## Reading Order

For current status, read [ROADMAP.md](ROADMAP.md), then
[ARCHITECTURE.md](ARCHITECTURE.md), then [SEARCH_ENGINE.md](SEARCH_ENGINE.md).

For query-understanding or routing work, read
[DB_GROUNDED_QUERY_UNDERSTANDING.md](DB_GROUNDED_QUERY_UNDERSTANDING.md) and
[ANSWER_ROUTING_DESIGN.md](ANSWER_ROUTING_DESIGN.md).

For v0.8.5/v0.8.6 planning, start with
[PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md](PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md),
then use [CLAUDE_CODE_LESSONS_APPLICATION_PLAN.md](CLAUDE_CODE_LESSONS_APPLICATION_PLAN.md)
as supporting design input.
