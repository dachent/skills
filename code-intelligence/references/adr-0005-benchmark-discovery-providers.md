# ADR-0005: Benchmark Graphify Against Codebase-Memory

- Status: accepted
- Date: 2026-07-12

## Context

Graphify is a useful mixed-media persistent graph, but Codebase-Memory presents a recent code-focused alternative with local MCP, hybrid semantic resolution, incremental indexing, and strong project-reported performance. Exact semantic systems such as Serena and SCIP also exceed tree-sitter-only graphs on symbol correctness.

## Decision

Do not designate Graphify as the universal or permanent discovery provider. Implement provider-neutral routing, retain Graphify as the initial mixed-media option, and create a benchmark workstream for Codebase-Memory and exact semantic providers.

## Consequences

- The architecture can adopt a higher-quality engine without rewriting the router.
- Default-provider selection is delayed until reproducible results exist.
- The initial implementation remains useful while avoiding premature lock-in.
