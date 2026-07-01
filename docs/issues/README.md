# docs/issues

Updated: 2026-07-01

This folder contains issue notes and design follow-ups. Current active ordering
is governed by `docs/DB_GROUNDED_QUERY_UNDERSTANDING.md` and
`docs/implementation/CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md`.

## Current Priority Order

1. v0.8.1 Active QA/Search Bug Bash and current-scope hardening - completed.
2. v0.8.2 Direction/Roadmap Alignment - completed.
3. v0.8.3 DB-Grounded Query Understanding / Meaning Search - implemented.
4. v0.8.4 Regression Cleanup - completed.
5. Documentation Map / Naming Cleanup - completed.
6. v0.8.5 Claude-Code Lessons Architecture Alignment - next.
7. v0.8.6 Minimal Runtime + Context Foundation - planned.
8. v0.9 Summary/Analysis/Research Writer foundation - blocked until the final v0.8.x audit.

## Included Notes

| Document | Role |
| --- | --- |
| `ROUTING_QA_ISSUES.md` | Current routing/QA issue log and v0.8.3 regression checklist. |
| `LLM_SEMANTIC_PARSER_PRIORITY.md` | Historical and supporting notes for LLM semantic parsing. |
| `CONVERSATION_STATE_FOLLOWUP.md` | ConversationState follow-up handling notes. |
| `GROUNDED_WRITER_STYLE_CONTROLLER.md` | Future grounded writer/style controller notes; blocked behind v0.8.x. |
| `EVAL_AND_DOCS_SYNC_ISSUES.md` | Evaluation and documentation sync notes. |
| `DOCUMENTED_ISSUES_SUMMARY.md` | Older documented issue summary. |

## Current Gate

Writer work should not start before DB-Grounded Query Understanding,
v0.8.5 architecture alignment, v0.8.6 minimal runtime/context foundation, and
the final v0.8.x audit are complete. Until then, `summary`, `analysis`, and
`research` should remain conservative future routes unless the specific
writer/executor is actually implemented.
