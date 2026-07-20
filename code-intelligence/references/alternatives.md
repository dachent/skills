# Alternatives and Value Assessment

Reviewed: 2026-07-12

## Conclusion

The optimal current design is not the largest provider set. It is the smallest set that covers recurring needs with distinct, measurable value.

The active Claude Code router stack is direct source, Graphify, `code-mapper-skill`, and mapper-owned selective CodeQL. Durable planning remains harness-native. Only Codebase-Memory remains a credible near-term substitution candidate, and only for Graphify's code-only discovery role.

## Truly high-value components

| Component | Decision | Why it earns its cost |
| --- | --- | --- |
| Direct source and tests | Keep | Final authority and universal fallback; no setup or staleness risk. |
| Graphify | Keep initially | Differentiated mixed-media and broad repeated discovery; already central to the routing problem. |
| `code-mapper-skill` | Keep | Unique Python imports, impact, artifacts, contracts, APIs, catalogs, and lineage in one structured workflow. |
| Selective CodeQL in code-mapper | Keep | Adds semantic value/taint paths that syntax graphs cannot provide, while remaining gated. |
| Graph freshness preflight | Keep | Prevents stale answers and avoids loading a large graph merely to choose a route. |
| Exact-target fast path | Keep | Protects the existing mapper's latency and deterministic behavior. |
| Router/discovery benchmarks | Keep | Prevent provider preference from becoming opinion or permanent lock-in. |

## Benchmark-only substitution

### Codebase-Memory

Codebase-Memory is the only near-term substitution worth testing. Its project reports a local persistent graph, MCP tools, incremental updates, semantic and structural search, impact analysis, and lower agent token/tool use.

It is not active because the evidence is recent and largely project-reported, while Graphify has a distinct mixed-media role. Benchmark it against Graphify and direct source on pinned repositories. Replace Graphify for code-only work only after a material, reproducible win and an acceptable license, privacy, freshness, and operations review.

## Customization without demonstrated value

### Serena

Dropped. It may improve semantic navigation and refactoring, but adding a new agent-facing semantic-editing subsystem is outside the concrete Graphify-versus-code-mapper routing problem. Host-native IDE or language-server tools can remain available independently.

### Joern and codebadger

Dropped. Their code-property-graph, slicing, and vulnerability-research capabilities are real, but deployment and maintenance cost is high and the recurring requirement has not been demonstrated. Existing selective CodeQL is sufficient for the current scope.

### SCIP and Sourcegraph

Deferred. They are valuable at enterprise cross-repository scale, but require indexers, build integration, storage, and operating infrastructure not justified by the current local skill repository.

### Semgrep

Do not integrate into this router. Semgrep is useful for rule-based CI and policy checks, but it is not a general repository-understanding provider and can remain a separate workflow.

### Aider-style repository map

Do not integrate. Its context-ranking design is useful reference material, but a second lightweight structural map would overlap Graphify and direct source exploration without solving a distinct current problem.

### Generic LSP/provider framework

Do not build. A generic registry, adapter SDK, or normalized graph schema would create a platform-maintenance burden before there are enough proven providers to justify it.

## Final selection

```text
Broad repeated discovery or mixed media -> fresh Graphify
Known Python structure/impact/lineage     -> code-mapper-skill
Python value/taint path when triggered    -> code-mapper + selective CodeQL
Durable planning deliverable              -> harness-native planning workflow
Everything else or any stale state        -> current source and tests
```
