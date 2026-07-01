# Research Loop Design

Status: future architecture design. Explicitly deferred until v0.11/v0.12.

Research mode is the eventual multi-call, multi-stage path for lore hypotheses,
counter-evidence, and uncertainty. This document defines the target shape so
v0.8.6 and v0.9 do not accidentally build incompatible shortcuts.

## Research Mode Is Multi-Stage

Research questions are not single lookup or single writer calls. They often ask
whether a relation, identity, motif, or theory is plausible. The system must
search official text, read context, compare hypotheses, look for counter
evidence, and decide whether further work is useful.

Example research-style queries:

- "Could Phanes and the Heavenly Principles be the same entity?"
- "Check official evidence and counter-evidence for Paimon's identity."
- "Can Irminsul memory manipulation connect to Celestia?"

These need staged investigation, not a direct confident answer.

## Expected Structure

Target research pipeline:

```text
Semantic Parser
-> Research Planner
-> DB Search / Source Reader
-> Evidence Judge
-> Counter Evidence Search
-> Gap Analyzer
-> Stop Controller
-> Final Reasoner
-> Writer / Validator
```

Responsibilities:

| Stage | Responsibility |
| --- | --- |
| Semantic Parser | Identify route, query type, focus entities, relation/hypothesis form, and risk flags. |
| Research Planner | Break the question into subquestions, hypotheses, search tasks, and evidence targets. |
| DB Search / Source Reader | Run deterministic searches and read source windows/sections/documents. |
| Evidence Judge | Classify evidence as support, weak support, context, counter, ambiguous, or translation note. |
| Counter Evidence Search | Search for texts that weaken or complicate the hypothesis. |
| Gap Analyzer | Identify missing evidence, low coverage, unresolved ambiguity, and next useful actions. |
| Stop Controller | Decide whether to answer, search more, abstain, or ask for narrowed scope. |
| Final Reasoner | Compare evidence and hypotheses under source-level constraints. |
| Writer / Validator | Produce grounded output and reject unsupported or overclaimed conclusions. |

## Stop Decision Criteria

The Stop Controller should consider:

| Criterion | Question |
| --- | --- |
| answerability | Can the current evidence support a useful answer? |
| expected information gain | Would one more search/read likely change the result? |
| counter-evidence coverage | Has the system looked for weakening or alternative evidence? |
| uncertainty resolvability | Is the remaining uncertainty searchable, or inherent to canon ambiguity? |
| budget/turn limit | Has the configured search/window/model budget been reached? |
| scope drift | Is the loop chasing topics outside the user's question? |

Stop decisions:

```text
answer
search_more
abstain_with_uncertainty
ask_to_narrow_scope
```

The loop must not continue just because a model can imagine another angle. It
should continue only when expected information gain is meaningful.

## Research State

Future research state should preserve:

- research goal,
- subquestions,
- hypotheses,
- search tasks,
- source windows read,
- evidence classifications,
- counter-evidence attempts,
- unresolved gaps,
- stop decision,
- final limitations.

Hypothesis statuses should include:

```text
open
plausible_but_unproven
weak
contradicted
unsupported
needs_more_evidence
```

## Target Stage

| Stage | Scope |
| --- | --- |
| v0.8.5 | Documentation architecture only. |
| v0.8.6 | TurnContext and PromptPackage can carry future research-route status, but no loop. |
| v0.9 | Writer foundation may produce evidence-grounded summary/analysis; full research loop remains out of scope. |
| v0.10 | Tool Engine / Execution Plan prepares deterministic tools. |
| v0.11 | Research Planner / Evidence Judge / Gap Analyzer. |
| v0.12 | Agentic Research Loop V1. |

## Deferred Status

Do not implement in v0.8.6 or v0.9:

- repeated research loop,
- automatic counter-evidence iteration,
- hypothesis memory lifecycle,
- multi-agent planner/scout architecture,
- workspace memory product,
- vector/motif/graph research expansion as a primary dependency.

v0.9 may prepare writer contracts that make this future loop possible, but it
must not claim full research mode is implemented.
