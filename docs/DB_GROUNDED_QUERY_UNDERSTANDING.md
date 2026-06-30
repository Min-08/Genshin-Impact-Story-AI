# DB-Grounded Query Understanding

Status: direction document for v0.8.2.

This document defines the query-understanding direction that must be completed
before v0.9 writer work begins. It is a product and architecture contract, not
an implementation record. The `query_understanding` module described here is
planned for v0.8.3 and is not implemented yet.

## Product Direction

This project is not a fast FAQ bot. It should behave like a deliberate Genshin
Impact lore research assistant: it should inspect official data, understand
what the user is probably asking about, expose uncertainty, and answer only
from grounded DB/source evidence.

The system must not optimize primarily for speed. A slow conservative answer is
better than a fast wrong answer. Latency is still a UX concern, but correctness,
source visibility, and recoverable uncertainty are higher priorities.

The target interaction is:

```text
user query
-> DB-grounded candidate search
-> candidate meaning comparison
-> LLM semantic adjudication when useful
-> deterministic DB/entity validation
-> route decision
-> search / Source Reader / Evidence Pack
-> answer or conservative fallback
```

The key change is that the system should search and inspect the DB to
understand the query before final routing. Routing must not be decided only from
keyword heuristics or from an unsupported LLM guess.

## Glossary

DB-Grounded Query Understanding
: The planned v0.8.3 layer that searches/inspects DB-backed candidates before
final route selection.

Meaning Search
: The candidate-search part of DB-Grounded Query Understanding. It gathers
possible user meanings from exact lookup, aliases, lore concept seeds, titles,
text units, and source-readable results.

Candidate Meaning Pack
: The structured diagnostics package that lists possible meanings, match
strength, source handles, LLM adjudication, and selected route contract.

supported_entity
: A current structured QA target that can safely produce `basic_lookup` output.

lore_concept
: A DB/source-backed lore topic or concept that should be searched or
investigated, not forced into structured `basic_lookup`.

strong match
: A safe exact/alias/content-type-compatible match.

weak match
: A partial, fuzzy, title-like, or context-dependent match that can inform
search but cannot by itself trigger `basic_lookup`.

unsafe match
: A candidate whose overlap is likely accidental or whose content type conflicts
with intent.

future-route
: A route that may be detected but whose writer/executor is not implemented.

source-readable result
: A result with handles such as `unit_id`, `document_id`, or `section_id` that
can be opened through Source Reader.

## Why Meaning Must Be DB-Grounded

The local DB already contains the project's official source universe: entities,
titles, aliases, text units, documents, sections, language variants, and search
signals. Query meaning should be inferred against that universe.

A raw user string can overlap with several things:

- A supported gameplay data entity, such as an avatar, weapon, or reliquary.
- A lore concept, such as Heavenly Principles, Irminsul, Celestia, or a motif.
- A document/title/text-unit phrase.
- A conversational follow-up to the previous turn.
- An unsupported gameplay, recommendation, or meta request.

If the resolver promotes weak text overlap directly into `basic_lookup`, the
system can answer the wrong question with high confidence. Meaning-first
routing avoids that by collecting candidates first and asking: "What DB-backed
interpretations exist, and which one is safe enough to execute?"

## Existing Failure Modes

Representative failures this direction is meant to prevent:

- A user asks "What is Cheonri / Heavenly Principles?" and weak partial overlap
  sends the request to a weapon or title lookup instead of lore exploration.
- A short explicit topic, such as "sun" or "Heavenly Principles", is hijacked by
  `last_entity` context from the previous character or weapon answer.
- A lore concept is promoted to avatar/weapon/reliquary `basic_lookup` because
  one token overlaps with a supported exact-lookup entity.
- The LLM parser proposes a route or entity that does not exist in the DB, and
  the answer layer treats it as factual.
- A broad lore question is handled by the structured QA path even though the
  current writer stack only supports deterministic `basic_lookup` answers.

## LLM Role And Limits

LLM-based intent understanding is important and should be strengthened, not
removed. Natural language questions are ambiguous, multilingual, elliptical,
and often ask about concepts that are not represented as clean structured
entities.

The LLM should act as a semantic adjudicator over DB-grounded candidates:

- Interpret the user's wording and requested depth.
- Compare candidate meanings when deterministic signals are close.
- Detect relation, summary, analysis, research, and follow-up intent.
- Explain ambiguity in structured debug output.
- Propose searches or source-reading plans for non-basic routes.

The LLM must not be the final fact authority:

- It must not invent entities, IDs, titles, stats, source claims, or relations.
- It must not promote an unsupported candidate to `basic_lookup`.
- It must not override deterministic hard guards.
- Its output must be validated by deterministic DB/entity resolution and Source
  Reader evidence before answer generation.

## Target Architecture

Planned v0.8.3 module boundary:

```text
src/genshin_lore_db/search_engine/query_understanding.py
```

Planned responsibilities:

```text
understand_query(query, conversation_state, db) -> QueryUnderstanding

1. Normalize the query.
2. Run hard guards for chitchat, command, guide/meta/strategy, and unsupported
   gameplay requests.
3. Gather DB candidates from exact title/alias/entity lookup, lore concept
   seeds, title search, text-unit search, and prior conversation context.
4. Build a Candidate Meaning Pack.
5. Ask the LLM to adjudicate only over the candidate pack when useful.
6. Classify matches as strong, weak, or unsafe.
7. Produce a route decision and execution contract.
8. Preserve diagnostics for tests and bug bash review.
```

This module should sit before `route_answer_query()` makes final execution
decisions. It should feed the existing `basic_lookup`, `search`, `investigate`,
Source Reader, and later writer routes rather than replacing them.

## Candidate Meaning Pack

A Candidate Meaning Pack is the inspectable DB-grounded context used to decide
what the query could mean. It is not final evidence for an answer; it is the
evidence for routing and disambiguation.

Suggested shape:

```json
{
  "schema_version": "candidate_meaning_pack.v0.1",
  "query": "What is Heavenly Principles?",
  "normalized_query": "heavenly principles",
  "conversation_context_used": false,
  "candidates": [
    {
      "candidate_id": "concept:heavenly_principles",
      "surface": "Heavenly Principles",
      "candidate_type": "lore_concept",
      "source": "manual_concept_seed",
      "match_strength": "strong",
      "route_hint": "analysis",
      "source_readable": true,
      "evidence_handles": ["unit_id:...", "document_id:..."],
      "reason": "Known lore concept with source-readable text units."
    },
    {
      "candidate_id": "project_amber:weapon:...",
      "surface": "A Thousand ...",
      "candidate_type": "supported_entity",
      "source": "title_like",
      "match_strength": "unsafe",
      "route_hint": "none",
      "source_readable": true,
      "reason": "Only weak substring overlap; not safe for exact lookup."
    }
  ],
  "llm_adjudication": {
    "used": true,
    "selected_candidate_id": "concept:heavenly_principles",
    "confidence": 0.83,
    "reason": "The wording asks for a lore concept definition."
  },
  "selected_meaning": {
    "candidate_id": "concept:heavenly_principles",
    "route": "analysis",
    "supported_for_current_writer": false
  }
}
```

## Match Policy

`supported_entity`
: A DB entity whose current implementation can answer a structured
`basic_lookup` safely. At v0.8 this is limited to the implemented QA targets:
avatar basic info, weapon basic info/effect, and reliquary/artifact effects.

`lore_concept`
: A DB-backed concept, motif, title cluster, or source-readable lore topic that
can be searched/investigated but is not a structured `basic_lookup` entity.

`strong match`
: Exact or high-confidence alias/title/entity match with compatible content
type and compatible user intent. Strong supported-entity matches may route to
`basic_lookup` when no higher-risk route signal is present.

`weak match`
: Partial, substring, broad title, fuzzy, or context-dependent match. Weak
matches can be shown as candidates and used for `search`/`investigate`, but they
must not by themselves trigger structured `basic_lookup`.

`unsafe match`
: A match whose surface overlap is likely accidental, whose content type
conflicts with intent, or whose use would answer a different question. Unsafe
matches must not be used for final routing except as debug/ambiguity metadata.

Supported exact lookup should be strict. Lore concepts should not be promoted
to avatar/weapon/reliquary `basic_lookup` through weak partial overlap.

## Routing Policy

Routing should be meaning-first:

```text
hard guard
-> Candidate Meaning Pack
-> deterministic exact/alias/content-type validation
-> LLM semantic adjudication over candidates, if needed
-> route decision
```

Current route status:

- `basic_lookup`: implemented for supported structured QA targets.
- `search`: implemented as the current lore exploration path.
- `investigate`: implemented as the current research-oriented Evidence Pack
  path with source-readable candidates and evidence pin integration.
- `summary`: route/intent may be detected, but writer output is not implemented
  and should remain conservative.
- `analysis`: search/investigate foundation exists, but claim-based writer is
  not implemented.
- `research`: future route; not a full autonomous agent yet.

When the user asks a lore concept question, prefer source-readable `search` or
`investigate` behavior over incorrect `basic_lookup`. If the target writer does
not exist yet, return a clear current-scope fallback with useful search/source
handles instead of fabricating a final summary or theory.

## Conversation Context Policy

Previous conversation context is useful but dangerous. It should only be used
for genuinely low-information follow-ups.

Use previous `last_entity` or `last_sources` only when the new query is
underspecified, for example:

- "tell me more"
- "what about the story?"
- "show the source"
- "and the materials?"

Do not inherit previous context when the new query introduces an explicit new
topic, entity, concept, title, or relation. Explicit new topics must not be
hijacked by `last_entity` context.

The Candidate Meaning Pack should expose:

- Whether context was considered.
- Whether context was used.
- Which context key was used.
- Why context was rejected for explicit-topic queries.

## Source Reader And Evidence Integration

Query understanding must connect meaning to source-readable results. A candidate
is stronger when it can be opened through Source Reader handles such as
`unit_id`, `document_id`, `section_id`, `canonical_id`, `language`, and
`source_url`.

`source-readable result`
: A search or candidate result that can be opened with Source Reader without
guessing a second identifier.

Meaning Search should return candidates that are useful for:

- `python -m genshin_lore_db search ... --with-window`
- `python -m genshin_lore_db read-window <unit_id>`
- `python -m genshin_lore_db read-document <document_id>`
- `python -m genshin_lore_db pin-evidence ...`
- `investigate()` candidate and pinned evidence fields

The LLM may explain or rank candidate meanings, but answer claims still need
Evidence Pack, Source Reader spans, or structured DB facts depending on route.

## Testing Strategy

v0.8.3 should add tests at three levels:

- Unit tests for candidate gathering, match strength classification, and
  context rejection.
- QA/routing regression tests for known ambiguous queries and explicit-topic
  follow-ups.
- Evaluation cases that check both route and candidate diagnostics.

Required test families:

- Strict supported entity exact lookup remains stable.
- Lore concepts do not become structured `basic_lookup` from weak overlap.
- Explicit new topics ignore previous `last_entity`.
- Low-information follow-ups can use prior context.
- LLM adjudication cannot invent DB candidates.
- Unsafe candidates are visible in diagnostics but not selected.
- Search/investigate candidates include source-readable handles.
- Summary/analysis/research writer claims remain marked not implemented until
  v0.9+ work actually exists.

## Staged Roadmap Before v0.9

v0.8 implemented:

- Source Reader workflow.
- JSONL evidence pin store.
- `pin-evidence`, `evidence list`, and `evidence show` CLI behavior.
- `investigate()` candidate/pinned evidence fields.
- Existing deterministic `basic_lookup` QA and validation.

v0.8.1 fixed/hardened:

- Active QA/search bug bash for the current scope.
- Stronger partial title matching for lore concepts and titles.
- Conservative story/follow-up context so explicit topics are not hijacked by
  `last_entity`.
- Regression tests for ambiguous lore terms, exact supported lookup, and
  context behavior.

v0.8.2 current documentation goal:

- Align roadmap and docs around DB-Grounded Query Understanding.
- State that speed is not the primary optimization target.
- Block v0.9 writers until meaning-first routing is implemented and tested.

v0.8.3 planned implementation:

- Add DB-Grounded Query Understanding / Meaning Search.
- Add Candidate Meaning Pack diagnostics.
- Add strong/weak/unsafe match policy in code.
- Strengthen LLM semantic adjudication while validating every result against
  DB candidates and Source Reader evidence handles.

v0.8.4 planned cleanup:

- Regression cleanup after v0.8.3.
- Expand bug bash cases.
- Confirm route/status metadata matches answer behavior.
- Remove or correct any docs that still imply unimplemented writers exist.

v0.9+ planned writer work:

- Summary/analysis/research writer implementation can begin only after v0.8.x
  stabilization and v0.8.3 query understanding are complete.
- Writer output must remain evidence-grounded and validated by Source Reader,
  Evidence Pack, and deterministic DB contracts.

## Future-Route Definition

`future-route`
: A route or answer contract that may be detected by router metadata but whose
writer/executor is not implemented yet. A future-route must not produce a fake
answer. It should return a clear unsupported/current-scope message and, when
useful, source-readable search or investigate results.

At v0.8.2, broad `summary`, claim-based `analysis`, and full `research` writers
are future-route work. The current lore exploration path is `search` and
`investigate`.
