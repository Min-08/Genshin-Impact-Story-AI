# LLM Runtime Profiles

Status: v0.8.5 architecture contract for v0.8.6 implementation planning. Not
implemented yet.

This document defines the LLM runtime profile boundary that v0.8.6 should
implement before v0.9 writer work starts. It turns the PM-approved direction in
`docs/PROJECT_FINAL_VISION_AND_ARCHITECTURE_DIRECTION_REVISED.md` into a
concrete implementation contract while keeping full provider integration
deferred.

## Purpose

The project already has deterministic QA, local Ollama rewrite support, and
DB-Grounded Query Understanding. v0.9 writer work will need separate model
roles instead of a single global `use_llm` flag or one hard-coded model name.

LLM runtime profiles should provide:

- Named execution modes for deterministic, local, API, and mixed operation.
- Role-specific model selection.
- Deterministic fallback behavior for every role.
- A stable config/schema boundary that writer and reasoner code can consume
  later without reading ad-hoc CLI flags directly.

This is an architecture and contract layer. It does not make the LLM the fact
authority. DB resolution, Source Reader handles, Evidence Pack, validators, and
hard guards remain authoritative.

## Role Separation

| Role | Purpose | Current or Target Use |
| --- | --- | --- |
| `router` / semantic parser | Interpret user intent and compare DB-grounded candidates. | Supports query understanding; must be validated against DB candidates. |
| `reasoner` | Compare evidence, structure interpretations, and decide uncertainty. | Planned for v0.9+ writer/reasoner work. |
| `writer` | Turn approved facts/evidence/claims into user-facing Korean prose. | Current local rewrite exists for `basic_lookup`; broader writer use is v0.9+. |
| `validator` | Assist validation where deterministic checks need semantic support. | Optional support only; deterministic validation remains final. |

The same model may serve multiple roles in a local profile, but the profile
schema must keep the roles separate so v0.9 can select and audit them
independently.

## Planned Config Files

v0.8.6 should add config files with conservative defaults:

```text
config/
  llm_profiles.json
  execution_modes.json
  router_models.json
  reasoner_models.json
  writer_models.json
  model_runtime_defaults.json
```

Suggested responsibility:

| File | Responsibility |
| --- | --- |
| `llm_profiles.json` | Named top-level profiles that map roles to providers/models and fallback settings. |
| `execution_modes.json` | Allowed execution modes and whether API use is permitted. |
| `router_models.json` | Models approved for semantic parser/router work. |
| `reasoner_models.json` | Models approved for evidence reasoning. |
| `writer_models.json` | Models approved for final prose/rewrite. |
| `model_runtime_defaults.json` | Timeout, retry, temperature, token budget, and fallback defaults. |

Profiles should be declarative. Code should validate them before use and expose
an explicit selected profile object to callers.

## Planned Runtime Modules

v0.8.6 should add the minimal runtime package:

```text
src/genshin_lore_db/llm/
  __init__.py
  runtime_profile.py
  profile_loader.py
  provider_config.py
  runtime_selector.py
```

Suggested responsibility:

| Module | Responsibility |
| --- | --- |
| `runtime_profile.py` | Dataclasses or typed models for profile, role binding, execution mode, fallback policy, and validation errors. |
| `profile_loader.py` | Load JSON config files, merge defaults, validate names/roles/providers, and return `RuntimeProfile`. |
| `provider_config.py` | Normalize provider identifiers such as deterministic, ollama, or api-placeholder. |
| `runtime_selector.py` | Resolve CLI/profile overrides into one selected runtime profile without executing model calls. |

v0.8.6 may connect existing local Ollama behavior where low risk, but it should
not require production-grade API provider execution.

## Execution Profiles

Required named profiles:

| Profile | Router | Reasoner | Writer | Validator | Intended Use |
| --- | --- | --- | --- | --- | --- |
| `deterministic` | deterministic | none | template | deterministic | CI, offline fallback, regression tests. |
| `local-full` | local | local | local | deterministic/local optional | Local developer full-LLM path. |
| `local-router-api-reasoner` | local | API | API or local | deterministic/local optional | Cheap local routing with stronger remote reasoning later. |
| `api-router-local-reasoner` | API | local | local | deterministic/local optional | Remote semantic parser, local answer drafting. |
| `api-full` | API | API | API | deterministic/API optional | Future full API mode. |

The mixed and API profiles may exist as config contracts before their providers
are fully executable. If a selected provider is unavailable, the runtime must
fall back or fail with a structured unsupported-runtime error.

## Fallback Policy

Fallback is part of the contract, not an error afterthought.

Required rules:

1. `deterministic` must always be available.
2. Router/semantic parser failure falls back to deterministic query
   understanding and hard guards.
3. Writer failure falls back to template or evidence-summary output.
4. Reasoner failure falls back to conservative Evidence Pack or source-handle
   output, not fabricated claims.
5. Validator failure must not approve output. It should either run deterministic
   checks only or reject the LLM draft.
6. Missing API credentials or unavailable local models must produce structured
   diagnostics and keep CLI sessions alive when a deterministic path exists.

The selected profile should expose fallback decisions in debug output so route,
answer, and future writer tests can assert the behavior.

## CLI Option Plan

Recommended v0.8.6 CLI shape:

```powershell
python scripts/lore_chat.py --llm-profile deterministic
python scripts/lore_chat.py --llm-profile local-full
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

Overrides should be parsed into a runtime profile object. Business logic should
not read scattered CLI flags after profile selection.

## v0.8.6 Implementation Checklist

v0.8.6 should implement:

- JSON config files listed above.
- Dataclasses or typed models for profiles and role bindings.
- Config loader with schema/shape validation.
- Runtime selector that resolves profile name plus optional overrides.
- Deterministic fallback profile available in all environments.
- Local Ollama binding for already-supported behavior where low risk.
- Debug output that reports selected profile, role bindings, and fallback state.
- Tests for valid profiles, invalid profiles, missing models/providers, and
  deterministic fallback.

v0.8.6 may add CLI option plumbing if it can do so without changing answer
behavior unexpectedly.

## Deferred Work

Defer all of the following beyond v0.8.6 unless a later goal explicitly allows
them:

- Full production-grade multi-provider API execution.
- Billing, quota, or credential management.
- Tool-calling agent loops.
- Research loop model orchestration.
- Streaming model output integration.
- Frontend/API runtime selection UI.
- Workspace-specific model policy.

## v0.9 Consumption

v0.9 writer work should consume a selected `RuntimeProfile` instead of
constructing provider/model choices directly. Writers and reasoners should ask:

```text
Which role am I executing?
What provider/model does the selected profile allow for this role?
What deterministic fallback applies if that execution fails?
What debug metadata must be preserved?
```

If this contract is unstable after v0.8.6, v0.9 should start with Summary
Writer V1 only. If it is stable, v0.9 can consider Summary + Analysis
foundation.
