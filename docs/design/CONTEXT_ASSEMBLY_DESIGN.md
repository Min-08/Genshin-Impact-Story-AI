# Context Assembly Design

Status: v0.8.5 architecture contract for v0.8.6 implementation planning. Not
implemented yet.

This document defines the TurnContext and PromptPackage boundary that v0.8.6
should implement before v0.9 writer work. It is based on
`docs/PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md`,
`docs/CLAUDE_CODE_LESSONS_APPLICATION_PLAN.md`, and
`docs/DB_GROUNDED_QUERY_UNDERSTANDING.md`.

## Purpose

TurnContextAssembler builds the situation board that downstream writers,
reasoners, and validators will consume. It does not answer the user directly.

It should collect:

- What the user asked.
- What DB-Grounded Query Understanding selected or rejected.
- What conversation/source context is available.
- What route and future-route constraints apply.
- What search, answer, and evidence policies must constrain later output.

The output should be stable enough that v0.9 writers do not read raw route
dicts, raw search results, or ad-hoc evidence objects directly.

## Non-Goal: Not An Answer Engine

TurnContextAssembler must not decide lore claims such as:

- whether two concepts are the same entity,
- whether a theory is true,
- which unsupported route should be answered as if implemented,
- which unverified evidence supports a claim.

Those decisions belong to Source Reader, Evidence Pack, writer/reasoner, and
validator stages. Context assembly only packages current state and policy.

## Difference From Query Understanding

DB-Grounded Query Understanding answers:

```text
What could this query mean, based on DB-backed candidates and safe routing?
```

TurnContextAssembler answers:

```text
Given the selected meaning and current system state, what context and rules
should the next component receive?
```

Query Understanding remains the meaning-first diagnostic layer. Context
assembly wraps that result with conversation state, source context, policy
blocks, runtime-readiness metadata, and output constraints for later writers.

## Inputs

v0.8.6 should support these inputs:

| Input | Description |
| --- | --- |
| original query | Raw user query before normalization. |
| normalized query | Query after existing normalization. |
| query_understanding result | Current `QueryUnderstanding` diagnostics and selected meaning. |
| Candidate Meaning Pack | Candidates, match strength, route hints, source readability, and LLM adjudication metadata. |
| conversation state | Current session summary, last entity, last topic, last sources, and follow-up flags. |
| active entity/topic | Entity or topic selected by safe current context, if any. |
| source context | Whether previous source handles or evidence pins can be used safely. |
| route candidate | Current route candidate and future-route status. |
| search/investigate metadata | Source-readable handles, fallback diagnostics, candidate/pinned evidence summaries. |

If an input is unavailable, the context should say so explicitly instead of
silently omitting the field.

## Outputs

### TurnContext

TurnContext is the structured state passed to writers, reasoners, and debug
commands.

Minimum fields:

```json
{
  "schema_version": "turn_context.v0.1",
  "query": {
    "original": "파네스와 천리는 같은 존재야?",
    "normalized": "파네스와 천리는 같은 존재야?"
  },
  "semantic_state": {
    "route_candidate": "analysis",
    "future_route": true,
    "query_type": "relation_compare"
  },
  "candidate_meaning_pack": {
    "selected_candidate_id": "concept:phanes",
    "candidate_count": 2,
    "source_readable": true
  },
  "conversation": {
    "is_followup": false,
    "active_entity": null,
    "active_topic": null,
    "context_used": false
  },
  "source_context": {
    "available": true,
    "handles": []
  },
  "policies": {
    "search_policy": {},
    "answer_policy": {},
    "evidence_policy": {}
  },
  "diagnostics": {
    "unsupported_reason": null,
    "fallbacks": []
  }
}
```

### PromptPackage

PromptPackage is the writer/reasoner input assembled from TurnContext plus
route-specific instructions.

Minimum fields:

```json
{
  "schema_version": "prompt_package.v0.1",
  "role": "writer",
  "route": "summary",
  "system_instructions": [],
  "developer_instructions": [],
  "visible_task_summary": "",
  "current_query": "",
  "semantic_state": {},
  "candidate_meaning_summary": {},
  "evidence_handles": [],
  "answer_requirements": [],
  "grounding_constraints": [],
  "output_contract": {}
}
```

PromptPackage should be deterministic to build and inspectable in debug output.

## Planned Modules

v0.8.6 should add:

```text
src/genshin_lore_db/context_engine/
  __init__.py
  turn_context.py
  context_assembler.py
  context_blocks.py
  db_map_context.py
  search_policy_context.py
  answer_policy_context.py
  evidence_policy_context.py
  prompt_package_builder.py
```

Suggested responsibility:

| Module | Responsibility |
| --- | --- |
| `turn_context.py` | Dataclasses or typed models for TurnContext, SemanticState, diagnostics, and policy blocks. |
| `context_assembler.py` | Build TurnContext from query, query_understanding, conversation, and source/search metadata. |
| `context_blocks.py` | Shared typed blocks for query, conversation, source, route, and diagnostics. |
| `db_map_context.py` | Summarize what DB/source universes are available for this turn. |
| `search_policy_context.py` | Build search priority and allowed retrieval actions. |
| `answer_policy_context.py` | Build answer-mode constraints, future-route limits, and writer permissions. |
| `evidence_policy_context.py` | Build source/evidence requirements and pin/counter-evidence expectations. |
| `prompt_package_builder.py` | Convert TurnContext into route/role-specific PromptPackage. |

## Planned Schemas

v0.8.6 should add:

```text
schemas/
  turn_context.schema.json
  prompt_package.schema.json
  semantic_state.schema.json
```

Schemas should validate field presence, enum values, fallback metadata, and
future-route status. They should not require a full writer implementation.

## Policy Blocks

### Search Policy

The search policy should tell later components which retrieval path is allowed:

- exact supported entity lookup,
- source-readable `search`,
- Evidence Pack oriented `investigate`,
- Source Reader follow-up,
- future route with conservative fallback.

### Answer Policy

The answer policy should state:

- `basic_lookup` may answer only supported structured facts.
- `summary`, `analysis`, and `research` remain future routes until implemented.
- facts, interpretation, and speculation must be separated.
- unsupported gameplay/meta requests must not be promoted to official answers.

### Evidence Policy

The evidence policy should state:

- source-readable handles are required for source claims.
- TextMap-only candidates can aid discovery but are not exact source-readable
  text units.
- pinned evidence and candidate evidence must be distinguished.
- claims without evidence must be lowered or rejected.

## Debug Command Plan

v0.8.6 should expose a developer debug path such as:

```powershell
python scripts/lore_search_engine.py context "파네스와 천리 관계" --json
python scripts/lore_search_engine.py prompt-package "수메르 스토리 요약" --route summary --json
```

Exact command names may change, but the debug output must let tests and
developers inspect:

- selected route/future-route status,
- selected Candidate Meaning Pack summary,
- context inheritance decision,
- source/evidence availability,
- search/answer/evidence policy blocks,
- selected runtime profile name if available.

## Tests Expected In v0.8.6

v0.8.6 should add tests for:

- TurnContext includes original and normalized query.
- explicit new topics do not inherit stale active entity.
- low-information follow-ups can include safe source/entity context.
- lore concepts remain future-route/search/investigate contexts, not
  `basic_lookup`.
- unsupported gameplay/meta requests carry unsupported policy.
- PromptPackage includes grounding constraints and output contract.
- schema validation rejects missing route, missing query, invalid future-route
  state, and malformed evidence handles.
- deterministic fallback still builds context when LLM/runtime is unavailable.

## v0.9 Writer Consumption Plan

v0.9 writers should consume:

```text
TurnContext
-> PromptPackage
-> selected RuntimeProfile role
-> writer/reasoner output
-> validator
```

Writers should not re-resolve query meaning from scratch. They should use
TurnContext for route, policy, evidence availability, and limitations. If
TurnContext says the route is a future-route without an implemented writer, the
writer must not fabricate a final answer.

## Deferred Work

Do not implement these in v0.8.6:

- autonomous agent loop,
- recursive research loop,
- streaming UI,
- frontend integration,
- full API provider execution,
- workspace memory product,
- vector/motif/graph expansion.
