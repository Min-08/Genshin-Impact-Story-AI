# Agentic Loop Design

Status: future architecture design. Explicitly deferred; not implemented in
v0.8.5 or v0.8.6.

This document explains how Claude Code-style tool loops could map to this
project later without turning v0.8.6 into a premature autonomous agent.

## Purpose

A future agentic loop should let the system choose, execute, inspect, and repeat
grounded research actions until it has enough evidence or must stop. It should
operate over official DB/search/source tools, not over unconstrained web-like
freeform actions.

The eventual product value is:

- deeper lore research over multiple source passes,
- explicit counter-evidence search,
- recoverable uncertainty,
- repeatable tool traces,
- evidence-grounded reports rather than single-shot guesses.

## Claude Code Mapping

Claude Code-style behavior can be abstracted as:

```text
context
-> choose tool
-> execute tool
-> inspect result
-> update context
-> continue or stop
```

For this project, the loop must be narrower:

```text
TurnContext
-> ExecutionPlan
-> approved lore/source tool
-> structured tool result
-> Evidence/Gap state
-> StopDecision
-> continue, synthesize, or abstain
```

The model may propose actions, but deterministic tool contracts, budgets,
source-readable handles, and validators must constrain every action.

## Why Not Now

The project should not jump directly into an agent loop because:

- v0.8.6 still needs stable LLM runtime profiles.
- TurnContext and PromptPackage are not implemented yet.
- v0.9 writers do not yet consume a stable context boundary.
- Tool contracts are still scattered across CLI/search/source workflows.
- Research planner, evidence judge, and stop controller are not implemented.

Implementing an agent loop now would mix routing, retrieval, reasoning, writing,
and validation into one unstable runtime path.

## Future Tool Categories

Initial future tool categories:

| Tool Category | Purpose |
| --- | --- |
| `SearchEntity` | Resolve supported entities, aliases, concepts, and content-type hints. |
| `SearchQuest` | Search quest/archon/event story source units and ordered chains. |
| `SearchDialogue` | Search dialogue-like text units and nearby context. |
| `SearchBook` | Search books, volumes, and readable document series. |
| `ReadSource` | Read unit/window/section/document/parallel text through Source Reader. |
| `CompareEvidence` | Compare supporting, weak, ambiguous, and counter evidence groups. |
| `PinEvidence` | Persist selected source spans as evidence pins. |

Every tool should return structured data with source handles, diagnostics, and
limitations. Tool output should be safe to serialize in an execution trace.

## Relation To Tool Engine / Execution Plan

Before a free loop exists, v0.10 should build a deterministic Tool Engine and
Execution Plan layer:

```text
ExecutionPlan
-> tool registry
-> tool contract validation
-> search/source/evidence tool call
-> structured result
-> diagnostics
```

This lets route-specific writers and future planners use tools without granting
the model unrestricted control.

## Staged Target

| Stage | Status | Scope |
| --- | --- | --- |
| v0.8.5 | Current docs pass | Define architecture only. |
| v0.8.6 | Planned | Runtime profiles, TurnContext, PromptPackage. No agent loop. |
| v0.9 | Planned writer foundation | Writers consume context and evidence. No full research loop. |
| v0.10 | Future | Tool Engine / Execution Plan. |
| v0.11 | Future | Research Planner / Evidence Judge / Gap Analyzer. |
| v0.12 | Future | Agentic Research Loop V1. |

## Deferred Status

Agentic loop implementation is explicitly deferred. Do not implement in v0.8.6:

- autonomous repeated tool execution,
- multi-agent orchestration,
- open-ended planner/replanner loops,
- workspace memory mutation,
- frontend streaming trace integration.

The correct near-term path is:

```text
RuntimeProfile
-> TurnContext
-> PromptPackage
-> writer foundation
-> Tool Engine
-> Research Planner
-> Agentic Loop
```
