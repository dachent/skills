# ADR-0005: Benchmark Graphify Against Codebase-Memory Before Any Swap

- Status: accepted
- Date: 2026-07-12

## Context

Graphify is useful for mixed code and non-code corpora. Codebase-Memory presents a recent code-focused alternative with local MCP, incremental indexing, semantic and structural retrieval, and strong project-reported performance.

Adding both as permanent active providers would increase installation, freshness, documentation, and support complexity before the value of dual operation is known.

## Decision

Keep Graphify as the initial broad-discovery provider. Treat Codebase-Memory as a benchmark-only replacement candidate for code-only repositories. Do not implement an adapter or active route until issue #54 demonstrates a material reproducible advantage and licensing, privacy, freshness, and operational behavior are acceptable.

## Consequences

- The MVP remains small and usable.
- Mixed-media capability is preserved.
- A superior code-only provider can replace Graphify later without rewriting the routing boundary.
- Provider choice remains evidence-based rather than preference-based.
