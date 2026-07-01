# Project Final Vision and Architecture Direction — Revised Decisions

Status: PM-approved planning source of truth for v0.8.5, v0.8.6, and v0.9 sequencing.
Date: 2026-07-01
Project: Genshin-Impact-Story-AI

---

## 0. Purpose

This document updates the final vision / architecture direction with the user's decisions on the open questions.

It should be used before the documentation cleanup goal and before v0.8.5/v0.8.6 planning.

The goal is to prevent Codex or future contributors from confusing:
- current implementation
- near-term architecture contracts
- future runtime integration
- legacy documentation
- canonical roadmap

This document does not implement features. It defines the project management decision layer.

---

## 1. Confirmed Decisions

### Q1. Should v0.8.6 be added?

Decision: Yes.

v0.8.6 should be added between documentation alignment and v0.9 writer work.

Reason:
v0.8.3 implemented DB-Grounded Query Understanding, and v0.8.4 is regression cleanup. However, v0.9 writer work should not start directly on top of route/query diagnostics alone. The writer will need stable runtime contracts, LLM profile selection, and a TurnContext/PromptPackage boundary.

Therefore:

```text
v0.8.4 Regression Cleanup
↓
Documentation Cleanup
↓
v0.8.5 Claude-Code Lessons Architecture Alignment
↓
v0.8.6 Minimal Runtime + Context Foundation
↓
Final v0.8.x Audit
↓
v0.9 Writer Foundation
```

v0.8.6 is a safety layer that prevents v0.9 from becoming a large unstructured writer implementation.

---

### Q2. How much of the LLM profile / runtime mode system should be implemented?

Decision: Implement the highest useful level of architecture, but do not over-connect runtime behavior yet.

Recommended scope:
- config files
- schema/contract
- profile loader
- runtime selection object
- CLI option plumbing if low-risk
- deterministic fallback
- no mandatory external API dependency
- no full multi-provider production integration yet

PM judgment:
A higher-level implementation is justified here because LLM runtime selection is a foundational contract. If v0.9 writer is implemented without profiles, the project will likely hard-code local Ollama, one model name, or a boolean `use_llm`, and then need refactoring later.

This is exactly the kind of work that should be done before writer/reasoner implementation.

However, "highest level" does not mean "fully connected production-grade provider stack." The best boundary is:

```text
Implement configuration and routing of model roles now.
Implement real provider execution only where already supported or low-risk.
```

Target design:

```text
config/
├─ llm_profiles.json
├─ execution_modes.json
├─ router_models.json
├─ reasoner_models.json
├─ writer_models.json
└─ model_runtime_defaults.json

src/genshin_lore_db/llm/
├─ runtime_profile.py
├─ profile_loader.py
├─ provider_config.py
└─ runtime_selector.py
```

Required model roles:
- router / semantic parser
- reasoner
- writer
- validator

Required execution profiles:
- deterministic
- local-full
- local-router-api-reasoner
- api-router-local-reasoner
- api-full

Recommended CLI shape:

```powershell
python scripts/lore_chat.py --llm-profile local-full
python scripts/lore_chat.py --llm-profile deterministic
python scripts/lore_search_engine.py answer "천리" --llm-profile local-router-api-reasoner
```

Optional low-risk overrides:

```powershell
--router-provider ollama
--router-model qwen3:4b-instruct
--reasoner-provider api
--reasoner-model provider-default-reasoning-model
--writer-provider ollama
--writer-model qwen3:4b-instruct
```

Do not block v0.8.6 on full external API provider implementation.

---

### Q3. How much of TurnContextAssembler / PromptPackage should be implemented?

Decision: Implement the highest useful level of architecture, including dataclasses/schema and prompt package builder, but avoid full agent-loop connection.

PM judgment:
This should be implemented more fully than a placeholder.

Reason:
TurnContextAssembler is not a cosmetic abstraction. It defines what the writer/reasoner will receive. If v0.9 starts without it, the writer will probably read raw route dicts, raw search results, or ad-hoc evidence objects directly. That would make later agent loop and research loop integration harder.

Therefore v0.8.6 should include a real minimal TurnContextAssembler.

Recommended scope:

```text
src/genshin_lore_db/context_engine/
├─ __init__.py
├─ turn_context.py
├─ context_assembler.py
├─ context_blocks.py
├─ db_map_context.py
├─ search_policy_context.py
├─ answer_policy_context.py
├─ evidence_policy_context.py
└─ prompt_package_builder.py

schemas/
├─ turn_context.schema.json
├─ prompt_package.schema.json
└─ semantic_state.schema.json
```

TurnContext should include:
- original query
- normalized query
- query_understanding result
- selected candidate meaning
- conversation state summary
- active entity / active topic
- source context availability
- DB map summary
- search policy
- answer policy
- evidence policy
- current route candidate
- unsupported/future-route status
- diagnostic metadata

PromptPackage should include:
- system/developer instructions for the writer/reasoner
- visible task summary
- current query
- semantic state
- candidate meaning pack summary
- evidence/source handles
- answer requirements
- safety/grounding constraints
- output contract

Do not implement:
- autonomous tool loop
- recursive agent loop
- research loop repetition
- streaming UI
- full external API execution

The important part is to define and test the data boundary so v0.9 writer can consume it.

---

### Q4. How broad should v0.9 writer work be?

Decision: Follow the actual progress after v0.8.4/v0.8.5/v0.8.6.

Do not over-decide now.

PM rule:
- If v0.8.6 produces stable TurnContext/PromptPackage and LLM profile contracts, v0.9 can include Summary + Analysis foundation.
- If v0.8.6 exposes instability, v0.9 should start with Summary writer only.
- Research writer should remain future work unless Summary/Analysis foundation proves stable.

Recommended decision gate before v0.9:

```text
If final v0.8.x audit says:
- query_understanding stable
- context assembler stable
- prompt package stable
- LLM profile fallback stable
- search/investigate stable
then v0.9 = Summary + Analysis Foundation.

Otherwise:
v0.9 = Summary Writer V1 only.
```

---

### Q5. When should real connection / integration happen?

Decision: Actual connection is a later task. For now, implement architecture and code-level contracts only.

This means:
- Design the architecture now.
- Add config/schema/dataclasses/builders now.
- Do not wire every component into final runtime yet.
- Do not force the frontend/API/agent loop to consume it yet.
- Do not implement full external provider integration unless already low-risk.

PM interpretation:
This keeps v0.8.6 valuable without exploding scope.

Allowed in v0.8.6:
- profile loader
- runtime profile object
- TurnContextAssembler
- PromptPackageBuilder
- schema validation
- debug command
- unit tests
- optional CLI flag parsing if safe

Deferred:
- real API provider switching in production
- full writer/reasoner model execution
- agentic tool loop
- streaming frontend
- persistent workspace memory
- research loop

---

### Q6. Are documentation file moves allowed?

Decision: Yes.

Documentation files may be moved/renamed if content is preserved and links are updated.

Allowed:
- move implementation records into `docs/implementation/`
- move truly obsolete historical docs into `docs/legacy/`
- create `docs/README.md`
- add status banners
- update README documentation map
- fix cross-links

Not allowed:
- delete documentation
- hide important historical notes
- leave broken links
- silently change canonical meaning without status notes

---

### Q7. Is a legacy folder needed?

Decision: Yes, if the file is truly legacy.

Add a legacy/archive area for docs that are no longer source-of-truth but should be preserved.

Recommended:

```text
docs/
├─ README.md
├─ ROADMAP.md
├─ ARCHITECTURE.md
├─ DB_GROUNDED_QUERY_UNDERSTANDING.md
├─ ANSWER_ROUTING_DESIGN.md
├─ SEARCH_ENGINE.md
├─ implementation/
│  ├─ CODEX_EXECUTION_ROADMAP_V0_6_TO_V1_0.md
│  └─ ROADMAP_V2_IMPLEMENTATION_NOTES.md
├─ issues/
│  └─ ...
└─ legacy/
   └─ README.md
```

`docs/legacy/README.md` should explain:
- why these docs are preserved
- which canonical document supersedes them
- whether the content is partially outdated
- when they were moved

Status banners should be added to legacy documents:

```text
Status: Legacy / Superseded.
This document is preserved for historical context.
The current source of truth is: docs/ROADMAP.md.
```

---

## 2. Updated Project Sequence

The project should proceed as follows:

```text
Current:
D. v0.8.4 Regression Cleanup

Next:
D-Docs. Documentation Map / Naming Cleanup

Then:
v0.8.5 Claude-Code Lessons Architecture Alignment

Then:
v0.8.6 Minimal Runtime + Context Foundation

Then:
Final v0.8.x Audit

Then:
v0.9 Writer Foundation
```

---

## 3. Scope Boundaries

### D. v0.8.4 Regression Cleanup

Purpose:
Clean up regressions after v0.8.3.

Do not add new architecture.

---

### D-Docs. Documentation Map / Naming Cleanup

Purpose:
Make the documentation navigable.

Actions:
- update README
- create/update docs/README.md
- mark canonical/reference/implementation/legacy docs
- move files if appropriate
- create docs/implementation/
- create docs/legacy/ if needed
- fix links

No runtime implementation.

---

### v0.8.5 Claude-Code Lessons Architecture Alignment

Purpose:
Turn the Claude Code lessons and the project direction into architecture docs.

Actions:
- document TurnContextAssembler
- document LLM runtime profiles
- document future agent loop
- document research loop
- document visible thinking / streaming
- update roadmap with staged application

No large runtime implementation.

---

### v0.8.6 Minimal Runtime + Context Foundation

Purpose:
Add stable runtime contracts before writer work.

Actions:
- implement LLM profile config and loader
- implement TurnContext dataclass/schema
- implement PromptPackage builder
- implement context assembler
- add debug commands
- add tests

Avoid:
- full writer
- full reasoner
- full agent loop
- research loop
- streaming frontend

---

### Final v0.8.x Audit

Purpose:
Check that v0.8.x is stable enough for v0.9.

Must verify:
- query_understanding stable
- docs canonical map clear
- LLM profile contract stable
- TurnContext contract stable
- no accidental v0.9 feature creep
- tests pass
- manual smoke pass

---

### v0.9 Writer Foundation

Scope depends on final v0.8.x audit.

Preferred if stable:
- Summary writer foundation
- Analysis writer foundation
- Evidence-grounded answer package
- writer/reasoner profile selection
- answer validator

Fallback if unstable:
- Summary writer only

Research loop remains future work.

---

## 4. PM Rationale

The project is currently at the correct moment to add architecture contracts because:

1. DB/search/source/evidence infrastructure already exists.
2. Query Understanding is now implemented.
3. Writer/reasoner work has not yet deeply started.
4. Full agent loop and research loop are still future work.
5. Adding contracts now prevents expensive refactors later.

The right PM strategy is:

```text
Build contracts early.
Connect runtime gradually.
Avoid fake feature completion.
Avoid large uncontrolled rewrites.
```

This means Q2 and Q3 should aim for a high-quality architecture boundary now, while Q5 keeps actual integration deferred.

---

## 5. Final PM Decisions

```text
Q1: Add v0.8.6.
Q2: Implement high-level LLM profile architecture now; defer full provider integration.
Q3: Implement real TurnContext/PromptPackage foundation now; defer full agent connection.
Q4: Decide v0.9 writer scope after final v0.8.x audit.
Q5: Architecture/code contracts now; actual full connection later.
Q6: Documentation moves allowed.
Q7: Add legacy folder for truly superseded docs.
```

---

## 6. Next Prompting Order

Use this order for Codex goals:

```text
1. Finish D.
2. Run Documentation Map / Naming Cleanup.
3. Run v0.8.5 Architecture Alignment.
4. Run v0.8.6 Minimal Runtime + Context Foundation.
5. Run Final v0.8.x Audit.
6. Start v0.9 only if audit says ready.
```
