# Routing And QA Issue Log

Status: updated during v0.8.2 Direction/Roadmap Alignment.

This file tracks routing and QA issues found in the interactive answer path.
Historical v0.6.x issues remain useful as regression context, but the current
active direction is DB-Grounded Query Understanding before v0.9 writer work.

Canonical direction:

```text
docs/DB_GROUNDED_QUERY_UNDERSTANDING.md
```

## Current Status

Implemented/current:

- `basic_lookup` QA supports current structured targets only.
- `search` and `investigate` are the current lore exploration paths.
- Source Reader and Evidence Pin workflows exist.
- Local LLM can support rewrite/semantic parsing, but final facts are validated
  by deterministic DB/entity logic and validators.

Fixed in v0.8.1 QA/search bug bash:

- Supported exact lookup routes are hardened for current QA targets.
- Ambiguous lore terms are less likely to fall into wrong structured lookup.
- Explicit new topics are protected from stale `last_entity` context.
- Story/topic follow-ups use previous context only when the query is genuinely
  low-information.
- Regression tests cover supported lookup, ambiguous lore concepts, and
  conversation-context behavior.

Planned for v0.8.3:

- DB-Grounded Query Understanding / Meaning Search.
- Candidate Meaning Pack diagnostics.
- Strong/weak/unsafe match policy.
- LLM semantic adjudication over DB candidates.
- Deterministic validation of selected meanings against DB candidates and
  source-readable Search/Source Reader handles.

## Resolved Issue: Entity-Only Basic Lookup Routing

Historical symptom:

```text
User asks a character name or a plain "tell me about X" query.
Route metadata shows analysis, but QA facts resolve to character_basic_info.
```

Resolution:

- Deterministic entity resolution and AnswerPlan metadata now keep current
  supported QA behavior aligned.
- The regression expectation is that implemented structured supported-entity
  lookups remain `basic_lookup` when the match is strong and the query has no
  relation/analysis/research signal.

Remaining guard:

- v0.8.3 must avoid broadening this into weak partial matches. A supported
  entity match is safe only when it is strong and content-type compatible.

## Resolved Issue: Greeting Or Chitchat Promoted To QA

Historical symptom:

```text
User sends a greeting.
Fallback search hits a character quote and QA returns character info.
```

Resolution:

- Greeting/chitchat guard runs before supported QA resolution.
- Such inputs should not enter structured lookup or source search unless the
  user also supplies a real lore/entity topic.

## Resolved Issue: Route Metadata And QA Execution Mismatch

Historical symptom:

```text
route=analysis
intent=character_basic_info
answer is structured basic lookup
```

Resolution:

- AnswerPlan metadata and answer execution now share more of the same current
  QA decision path.
- Regression checks should continue comparing route, intent, selected target,
  validation status, and final answer mode.

## Active Risk: Weak Lore Overlap Becomes Wrong Basic Lookup

Problem:

Short lore concepts can partially overlap with supported entity titles. A weak
text/title match must not become avatar/weapon/reliquary `basic_lookup`.

Required v0.8.3 behavior:

- Build a Candidate Meaning Pack before final routing.
- Classify supported entity/title matches as strong, weak, or unsafe.
- Treat lore concepts as `lore_concept` unless there is a strong supported
  exact/alias/content-type match.
- Prefer source-readable `search` or `investigate` when the target is a lore
  concept and no implemented writer exists.

## Active Risk: Conversation Context Hijacks Explicit Topics

Problem:

Previous conversation context is helpful for "tell me more" follow-ups but
dangerous when the user asks a new explicit topic.

Required v0.8.3 behavior:

- Use `last_entity` or `last_sources` only for genuinely low-information
  follow-ups.
- Reject previous context when the query contains a new explicit topic, entity,
  concept, title, or relation.
- Emit diagnostics showing whether context was considered, used, or rejected.

## Active Risk: LLM Parse Treated As Fact Authority

Problem:

The LLM can understand natural language better than brittle heuristics, but it
can also invent or overconfidently select unsupported meanings.

Required v0.8.3 behavior:

- Keep LLM intent understanding as a core capability.
- Feed the LLM DB-grounded candidates instead of an open-ended authority role.
- Reject LLM candidates that cannot be found in deterministic DB/entity
  resolution.
- Validate answer claims through structured DB facts, Source Reader spans, or
  Evidence Pack depending on route.

## Writer Status

Do not file summary/analysis/research missing-writer behavior as a bug unless
the current route claims to be implemented. At v0.8.2:

- `summary`: future-route writer work.
- `analysis`: search/investigate foundation exists, final writer not
  implemented.
- `research`: future route, not an autonomous agent.

Current supported lore exploration path:

```text
search
investigate
Source Reader
Evidence Pin
```

## Regression Checklist

Future routing/QA bug bash passes should include:

- Strong supported entity exact lookup remains `basic_lookup`.
- Lore concept queries do not produce wrong weapon/avatar/reliquary answers.
- Explicit new topics ignore stale context.
- Low-information follow-ups can inherit context when appropriate.
- LLM semantic adjudication cannot invent unsupported entities.
- Search/investigate results expose source-readable handles.
- Future-route responses remain conservative until writers exist.
