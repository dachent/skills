# Repository Integration Contract

`skills-manifest.json` is the canonical inventory for supported top-level skills and shared runtimes.

## Required supported-skill package

Every supported skill must declare and provide:

- a top-level directory whose name matches the skill name;
- `SKILL.md` with matching front-matter `name` and a non-empty description;
- `agents/openai.yaml` with display name, short description, and default prompt;
- source classification, owner, supported platforms, supported agents, and review date in the manifest;
- hosted validation commands or an explicit environment-dependent validation declaration;
- `PROVENANCE.md` when the manifest declares a provenance file.

## Lifecycle states

- `supported`: documented, packaged, and subject to required validation;
- `experimental`: usable with explicitly documented limitations;
- `deprecated`: retained temporarily with replacement or removal guidance;
- `archived`: historical material not included in active integration checks.

## Source classifications

- `repo-owned-original`
- `local-source-import`
- `light-adaptation`
- `medium-adaptation`
- `heavy-adaptation`
- `derived-work`

External adaptations must identify an immutable source revision. Local-source imports must identify the initial repository commit and document unresolved source or license questions.

## Pull-request requirements

A pull request that adds or materially changes a skill must update, as applicable:

1. `skills-manifest.json`;
2. `SKILL.md`;
3. `agents/openai.yaml`;
4. `PROVENANCE.md`;
5. hosted or environment-dependent tests;
6. root documentation when user-facing installation or support behavior changes.

The repository validator fails when a top-level skill is not registered or a supported skill omits required packaging.

## GitHub Actions requirements

Hosted validation must expose a stable `Validate / Required` result and separately report repository integrity, static/contract checks, and behavioral tests. Jobs must use least-privilege permissions, explicit timeouts, and pull-request concurrency cancellation.

Office COM validation remains environment-dependent and must run through the separately controlled self-hosted workflow. Hardening that runner and separating trusted harness code from pull-request artifacts remains a dedicated follow-up workstream.
