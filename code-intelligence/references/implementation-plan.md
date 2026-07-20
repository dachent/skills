# Final Implementation Plan

## Goal

Ship a small, reliable control plane that solves two concrete problems:

1. prevent stale or unnecessary Graphify use; and
2. choose correctly between broad discovery, Python-specific analysis, and direct source inspection.

It is not a universal code-intelligence platform.

## Scope at merge

### Active

- direct source/search/tests;
- Graphify for broad discovery when an existing graph is fresh;
- `code-mapper-skill` for Python structure, impact, contracts, artifacts, catalogs, and lineage;
- selective CodeQL enrichment already exposed by `code-mapper-skill`;
- lightweight preflight, deterministic routing, evidence metadata, and tests.

### Benchmark-only candidate

- Codebase-Memory as a possible replacement for Graphify on code-only repositories.

### Out of scope

- Serena;
- Joern or codebadger;
- SCIP or Sourcegraph integration;
- Semgrep routing;
- Aider-style repository maps;
- generic LSP orchestration;
- automatic Graphify build or refresh;
- a dynamic provider registry or plugin SDK.

## Phase 0 — Repair PR #57

- add the referenced routing, provider-contract, and implementation documents;
- remove inactive provider references from instructions, routing code, preflight, tests, manifest description, generated catalog, PR text, and benchmark issues;
- add the adversarial review record;
- run the complete repository validation, not only skill-local tests;
- do not report completion until the required PR check is green.

## Phase 1 — Merge the minimal router

Acceptance criteria:

- all required CI checks pass;
- known Python targets route to code-mapper without Graphify I/O;
- broad discovery uses Graphify only when fresh;
- stale or missing graphs fall back to direct source;
- no inactive provider is emitted by `route.py` or detected by `preflight.py`;
- source verification remains mandatory.

## Phase 2 — Required benchmarks

### Router overhead

Track in issue #53. The known-target mapper route must stay within:

- 75 ms median absolute overhead;
- 5 percent median relative overhead;
- 200 ms p95 absolute overhead;
- zero Graphify subprocesses;
- zero `graph.json` reads.

### Discovery-provider value

Track in issue #54. Compare direct source, Graphify, and Codebase-Memory on pinned code-only and mixed-media repositories. Codebase-Memory remains unintegrated until the benchmark is complete.

A swap requires a material advantage, not a marginal win. At least one of the following must be demonstrated without a material precision regression:

- at least 10 percentage points better top-three target accuracy or key-fact recall; or
- at least 30 percent fewer model tokens or tool calls; or
- materially lower index/update/query cost with equivalent answer quality.

### Selective CodeQL value

Track in the narrowed security benchmark issue. Compare mapper output with and without selective CodeQL on representative Python source-to-sink tasks. CodeQL must add useful paths without imposing default overhead on unrelated mapper runs.

## Phase 3 — Provider decision

- Keep Graphify if it remains better overall or uniquely valuable for mixed-media projects.
- Replace Graphify for code-only discovery only if Codebase-Memory meets the benchmark gate and has acceptable licensing, privacy, freshness, and operational behavior.
- Do not add both permanently unless separate task classes demonstrably require both.

## Maintenance rules

- Every active provider must have an implemented route, a failure fallback, and a benchmark or explicit reason for exemption.
- Every path referenced from `SKILL.md` must exist and pass repository validation.
- Provider additions require an ADR and a benchmark issue before implementation.
- Completion means required CI is green, not that local tests passed.
