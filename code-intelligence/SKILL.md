---
name: code-intelligence
description: route repository understanding and change-impact work across direct source inspection, fresh Graphify data, code-mapper Python analysis, selective CodeQL enrichment, and durable repo-map planning. use for unfamiliar repositories, architecture questions, locating implementations, Python blast radius, contracts, artifacts, lineage, security-flow triage, graph freshness decisions, and choosing the lowest-cost reliable route. do not use for a trivial one-file edit whose source is already known.
---

# Code Intelligence

## Purpose

Act as a thin control plane for repository intelligence. Choose the least expensive implemented route that can answer the question reliably, preserve evidence provenance, and verify material conclusions against current source and tests.

Keep providers independent. This skill does not vendor or absorb Graphify, `code-mapper-skill`, CodeQL, or `repo-map-codex`.

## Active Routes

1. **Direct source and tests** — default for known non-Python targets, small repositories, stale or missing graph data, and final verification.
2. **Graphify** — broad or unknown-target discovery only when an existing graph is relevant and fresh.
3. **`code-mapper-skill`** — Python imports, callers, cycles, blast radius, artifacts, contracts, APIs, catalogs, and lineage.
4. **Selective CodeQL through `code-mapper-skill`** — Python security or value-flow questions when CodeQL is available and the mapper's documented trigger applies.
5. **`repo-map-codex`** — only when the user explicitly needs a durable planning map and evidence catalog.

Codebase-Memory is a benchmark candidate, not an active provider. Serena, Joern/codebadger, SCIP/Sourcegraph, Semgrep, and Aider-style maps are not part of the MVP routing surface.

## Workflow

1. Classify the request as broad discovery, known-target Python analysis, artifact or contract lineage, security-flow triage, durable planning, or direct source work.
2. Run `scripts/preflight.py` only when Graphify freshness or local capability matters. It must not parse `graph.json` merely to choose a route.
3. Apply `references/routing-policy.md`. Prefer the known-target fast path and do not build an index unless repeated discovery justifies it.
4. Follow `references/freshness-policy.md` before graph-backed work. Graph existence is not proof of freshness.
5. Follow `references/provider-contract.md` and record route, freshness, latency, evidence, warnings, and fallback use.
6. Verify against current source and tests.
7. Report stale evidence, unavailable capabilities, inferences, and unverified assumptions.

## Fast Rules

- Known Python file or symbol: `code-mapper-skill`, without Graphify I/O.
- Python artifact, contract, API, catalog, or lineage question: `code-mapper-skill`.
- Python security/value-flow question: `code-mapper-skill` with selective CodeQL when available; otherwise report the limitation.
- Broad unknown-target question: fresh Graphify if already available; otherwise direct source exploration.
- Known non-Python target or small repository: direct source and host-native tools.
- Durable planning artifact: `repo-map-codex` only on explicit request.

## Performance Boundaries

The direct route to `code-mapper-skill` must not read or parse Graphify's graph and must not spawn Graphify. The router itself adds no runtime overhead: routing is a decision tree applied in-context, not a process. `route.py` is an importable policy function (`decide_route`), never a subprocess in the request path — there is no CLI to spawn between the request and the selected provider.

## Required References

- `references/architecture.md`
- `references/routing-policy.md`
- `references/freshness-policy.md`
- `references/provider-contract.md`
- `references/alternatives.md`
- `references/implementation-plan.md`
- `references/adversarial-review.md`
- ADR files

## Bundled Scripts

- `scripts/route.py` — importable routing policy (`decide_route`); no CLI, not spawned at runtime
- `scripts/preflight.py` — Graphify freshness / capability check, run only when graph-backed work is in scope
- `scripts/test_route.py`
- `scripts/test_preflight.py`

Run scripts with Python 3.10 or newer. Do not report repository work complete until the PR's required checks have concluded successfully.
