# Routing Policy

## Objective

Choose the cheapest implemented route that is adequate for the question. Provider availability does not justify using a provider; task fit and freshness do.

## Decision order

1. **Python security or value-flow question** → `code-mapper-skill`; enable its selective CodeQL path only when CodeQL is available and the documented trigger applies.
2. **Known Python file or symbol** → `code-mapper-skill`, with no Graphify read or subprocess.
3. **Python artifacts, contracts, APIs, catalogs, or lineage** → `code-mapper-skill`.
4. **Known non-Python target** → direct source and host-native tools.
5. **Small repository** → direct source.
6. **Broad or unknown target with a fresh existing Graphify graph** → Graphify, then verify candidates in source; optionally hand Python candidates to `code-mapper-skill`.
7. **Graph missing, stale, unknown, or corrupt** → direct source; do not silently refresh or rebuild.

## Explicit non-routes

The supported router does not route to Serena, Joern/codebadger, SCIP/Sourcegraph, Semgrep, Aider-style maps, generic LSP adapters, or Codebase-Memory. Codebase-Memory remains a benchmark candidate only.

Durable planning is harness-native and outside this provider router. This skill is not for Codex GPT-5.6 Sol.

## Escalation rules

- Do not add a provider because it is theoretically stronger.
- Add or replace a provider only after a reproducible benchmark demonstrates material value on recurring tasks.
- Do not hide index creation, cloud upload, model calls, or long-running analysis inside routing.
- Provider failures must fall back to current source where possible.

## Output requirements

Every route decision should state:

- selected route;
- why cheaper routes were inadequate;
- graph freshness when Graphify is used;
- whether CodeQL enrichment was available and invoked;
- warnings and fallbacks;
- source and test verification performed.
