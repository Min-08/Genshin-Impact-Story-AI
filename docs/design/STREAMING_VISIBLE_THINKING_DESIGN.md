# Streaming And Visible Thinking Design

Status: future architecture design. Explicitly deferred until after core
writer/research foundations.

Visible thinking in this project means user-facing progress/status messaging.
It does not mean exposing private chain-of-thought or raw hidden reasoning.

## Policy

Do not expose:

- hidden chain-of-thought,
- raw model deliberation,
- unfiltered tool traces,
- private scoring details that imply unsupported certainty.

Do expose:

- current phase,
- user-safe progress summary,
- source/search/evidence actions at a high level,
- limitations or failure states,
- answer streaming when writer support exists.

## Example Phases

| Phase | User-Facing Meaning |
| --- | --- |
| semantic routing | Understanding the query and route. |
| candidate search | Finding DB-backed entities, lore concepts, and source candidates. |
| source reading | Reading source windows, sections, documents, or parallel text. |
| evidence building | Grouping supports, context, counter-candidates, and pinned evidence. |
| reasoning | Separating confirmed facts, interpretations, and uncertainty. |
| writing | Drafting the final user-facing answer. |
| validation | Checking grounding, unsupported claims, and fallback rules. |

Example messages:

```text
Identifying the likely lore concepts and route.
Searching source-readable official text candidates.
Reading nearby source context.
Separating confirmed evidence from interpretation.
Validating that answer claims have source support.
```

## Possible Event Names

The eventual backend event contract can use:

```text
run.started
router.started
router.completed
search.started
search.progress
search.completed
source_read.started
source_read.completed
evidence.started
evidence.completed
reasoning.started
writing.started
writing.delta
validation.started
run.completed
run.error
```

Future versions may add `context.started`, `context.completed`,
`source_read.progress`, `reasoning.completed`, `writing.completed`, and
`validation.completed`, but the above list is the minimum named set requested
for the v0.8.5 architecture alignment.

## Event Shape Draft

Future event shape:

```json
{
  "schema_version": "run_event.v0.1",
  "run_id": "run_...",
  "event": "search.progress",
  "phase": "candidate_search",
  "message": "Searching source-readable official text candidates.",
  "public": true,
  "payload": {
    "query": "천리",
    "candidate_count": 5
  }
}
```

Payloads should avoid private reasoning and should be safe to show in logs or a
frontend status panel.

## Target Stage

| Stage | Scope |
| --- | --- |
| v0.8.5 | Document event/phase direction only. |
| v0.8.6 | TurnContext/PromptPackage may include phase metadata if useful, but no streaming runtime. |
| v0.9 | Writer foundation may later emit writing events if scoped. |
| v0.10+ | Backend event contract after Tool Engine and writer foundations. |
| Later frontend stage | UI integration for progress/status and answer streaming. |

## Deferred Status

Do not implement in v0.8.6:

- streaming transport,
- frontend status components,
- browser UI event rendering,
- raw tool trace exposure,
- model reasoning deltas,
- private chain-of-thought display.

Visible progress should arrive only after the underlying route/context/source
contracts are stable enough to describe honestly.
