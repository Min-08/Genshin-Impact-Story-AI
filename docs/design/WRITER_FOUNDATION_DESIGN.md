# Writer Foundation Design

Status: v0.8.5 bridge design for v0.9 planning. Not implemented yet.

This document defines how v0.9 writer work should consume v0.8.6 outputs. It is
optional in the v0.8.5 goal, but useful because the final v0.8.x audit must
decide whether v0.9 starts with Summary Writer V1 only or Summary + Analysis
foundation.

## Inputs From v0.8.6

v0.9 writers should consume:

```text
RuntimeProfile
TurnContext
PromptPackage
Evidence Pack / Source Reader handles
structured DB facts
validator contracts
```

They should not:

- re-run query meaning from scratch,
- inspect raw CLI arguments for model selection,
- treat LLM output as source truth,
- bypass future-route status,
- invent source evidence.

## Scope Variants

### Variant A: Summary Writer V1 Only

Choose this if the final v0.8.x audit finds instability in TurnContext,
PromptPackage, runtime profiles, or search/source behavior.

Scope:

- summary scope contract,
- ordered source unit collection,
- extractive or conservative summary fallback,
- writer prompt package for summary only,
- coverage validator,
- deterministic fallback.

### Variant B: Summary + Analysis Foundation

Choose this only if the final v0.8.x audit says:

- query_understanding remains stable,
- context assembler is stable,
- prompt package is stable,
- LLM profile fallback is stable,
- search/investigate remains stable.

Scope:

- Summary Writer V1,
- analysis claim model,
- evidence-grounded analysis draft,
- source-level and qualifier validator,
- overclaim fallback,
- no full research loop.

Research writer should remain future work unless Summary/Analysis foundation
proves stable and the roadmap explicitly permits it.

## Grounding Constraints

All writer variants must:

- use structured DB facts for `basic_lookup`,
- use Evidence Pack and Source Reader handles for lore/source claims,
- distinguish confirmed facts, interpretations, speculation, and uncertainty,
- preserve source-level boundaries,
- reject or lower claims without evidence,
- avoid fake answers for future-route requests.

Writer output should be validated after generation. Validator failure should
drop to a conservative fallback, not retry into a less grounded answer.

## Output Contract Direction

Writer output should preserve:

```json
{
  "schema_version": "writer_output.v0.1",
  "route": "summary",
  "answer": "",
  "claims": [],
  "source_refs": [],
  "limitations": [],
  "validation": {
    "status": "pending",
    "checks": []
  }
}
```

For user-facing text, the system may hide internal IDs by default, but the
internal package must preserve source references for debugging and validation.

## No Full Research Loop In v0.9

v0.9 must not implement:

- autonomous research loop,
- multi-agent scout loop,
- persistent hypothesis memory,
- streaming frontend,
- vector/motif/graph as primary retrieval dependencies.

The writer foundation should prepare for these later systems by consuming
TurnContext and PromptPackage cleanly, not by embedding loop behavior inside
writer functions.
