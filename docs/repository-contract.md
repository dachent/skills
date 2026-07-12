# Repository integration contract

`skills-manifest.json` is the operational source of truth for supported skills, catalog grouping, ownership, platform and agent support, provenance classification, packaging, shared runtimes, validation, and generated mirrors.

## Canonical sources

Each active skill has one canonical top-level directory. `.claude/skills` may contain only mirrors declared in `generated_mirrors` and produced by `tools/generate_repository_artifacts.py`. Undeclared files there are drift.

## Catalog groups

Catalog groups explain why a skill belongs in the repository, not merely its technical domain. Every active skill belongs to exactly one ordered group declared in `policy.catalog_groups`. The README catalog is generated from those declarations.

## Generated artifacts

Run `python .\tools\generate_repository_artifacts.py` to generate the README catalog, installation inventory, platform/agent matrix, validation summary, declared agent mirrors, and `.generated/agent-mirrors.json`.

Run `python .\tools\generate_repository_artifacts.py --check` to fail on stale marked README sections, stale mirrors, stale hashes, or undeclared files under `.claude/skills`.

Generated README regions carry explicit markers and notices. Prose outside those markers remains hand-maintained.

## Agent mirrors

A mirror is allowed only when an agent needs a material packaging difference. Each declaration identifies a canonical source, a destination under `.claude/skills`, and an explicit transformation. `copy-with-generated-notice` preserves canonical content while inserting a generated-file notice after YAML front matter.

`.generated/agent-mirrors.json` records source and destination SHA-256 values. No mirrors are currently declared; compatible agents should load canonical top-level skills directly.

## Supported-skill package

Every supported skill must provide a top-level canonical directory, matching `SKILL.md`, `agents/openai.yaml`, catalog group, source classification, owner, platforms, agents, review date, and validation declarations. A provenance file is required when declared by the manifest.

External adaptations should identify an immutable upstream revision. When prior repository history did not preserve one, the source must explicitly declare `provenance_status: revision-unresolved`; this is a visible debt, not a substitute for provenance completion.

## Pull requests and CI

A skill-changing pull request updates the manifest, canonical skill package, provenance and tests as applicable, then regenerates repository artifacts. Repository-integrity CI runs manifest validation, generator check mode, generator tests, metadata validation, provenance checks, and Codex hook validation. Adding or removing a skill cannot leave the README stale, and canonical and generated definitions cannot silently diverge.

Office COM validation remains environment-dependent and runs through the controlled self-hosted workflow.
