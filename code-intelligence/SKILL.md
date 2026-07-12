---
name: code-intelligence
description: route codebase understanding and change-impact work across repository discovery, precise symbol analysis, artifact lineage, contracts, semantic flow, and durable planning. use for unfamiliar repositories, architecture questions, locating implementations, blast-radius analysis, callers and references, data lineage, security or taint flow, graph freshness decisions, and choosing among graphify, code-mapper, direct source inspection, repo-map, codeql, joern, serena, scip, or other configured providers. do not use for a trivial one-file edit when the relevant source is already known.
---

# Code Intelligence

## Purpose

Act as the control plane for repository intelligence. Select the least expensive provider that can answer the question reliably, preserve provider-specific evidence, and verify material conclusions against source and tests.

Do not absorb provider implementations into this skill. Keep `code-mapper-skill`, Graphify, language servers, SCIP, CodeQL, Joern, and other engines independently installable and independently fail-safe.

## Workflow

1. **Classify the request.** Determine whether it is discovery, exact symbol navigation, Python blast radius, artifact or contract lineage, semantic flow, security analysis, durable planning, or direct source work.
2. **Run a lightweight preflight.** Use `scripts/preflight.py` when local execution is available. Inspect only small metadata and status files. Do not load `graph.json` merely to decide whether to use it.
3. **Apply the routing policy.** Read `references/routing-policy.md`. Prefer the exact-target fast path when a file or symbol is already known.
4. **Establish graph freshness only when graph-backed retrieval is relevant.** Read `references/freshness-policy.md`. Treat graph existence as insufficient evidence of freshness.
5. **Invoke providers through explicit boundaries.** Follow `references/provider-contract.md`. Record provider, version, freshness, latency, evidence, warnings, and fallback use.
6. **Escalate only when needed.** Broad discovery may identify candidates for `code-mapper-skill`; suspicious flow may escalate to CodeQL or Joern; durable planning may invoke `repo-map-codex`.
7. **Verify before changing code.** Read the selected source, inspect relevant tests and contracts, and run the narrowest validation that can disprove the conclusion.
8. **Report limitations.** Distinguish extracted facts, inferred relationships, stale evidence, unavailable providers, and unverified assumptions.

## Fast Routing Rules

- Exact Python file or symbol, callers, imports, cycles, contracts, artifacts, or lineage: use `code-mapper-skill` first.
- Broad or unknown-target architecture question: use a fresh persistent graph if available; otherwise use direct repository exploration or build an index only when expected reuse justifies it.
- Exact multi-language symbol navigation or refactoring: prefer a configured LSP, Serena, SCIP, or compiler-backed provider.
- Data flow, taint, program slicing, or vulnerability analysis: prefer CodeQL or Joern/codebadger; use the current mapper's local CodeQL enrichment only for its documented narrow scope.
- Durable project map for planning: use `repo-map-codex`.
- Small repository or one known file: inspect source directly.

## Performance Boundaries

The direct route to `code-mapper-skill` must not read or parse a Graphify graph and must not spawn a Graphify process. Target router overhead is at most 75 ms median, 200 ms p95, and 5 percent relative to the mapper baseline. See `references/benchmark-plan.md`.

## Required References

- Read `references/architecture.md` for system boundaries and execution flow.
- Read `references/routing-policy.md` before adding or changing a route.
- Read `references/freshness-policy.md` before using persistent graph data.
- Read `references/provider-contract.md` before integrating a provider.
- Read `references/alternatives.md` when selecting or replacing an engine.
- Read `references/implementation-plan.md` for phased delivery and acceptance gates.
- Read the ADR files before changing the architectural boundaries they govern.

## Bundled Scripts

- `scripts/route.py`: deterministic routing decision helper.
- `scripts/preflight.py`: low-overhead provider and Graphify-state inspection.
- `scripts/benchmark_router_overhead.py`: alternating baseline/candidate wall-time harness.
- `scripts/test_route.py` and `scripts/test_preflight.py`: contract tests.

Run scripts with Python 3.10 or newer. Scripts are advisory control-plane utilities; provider output and source code remain the final evidence.
