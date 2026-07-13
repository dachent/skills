# ADR-0003: Preserve Provider-Specific Evidence

- Status: accepted
- Date: 2026-07-12

## Context

Tree-sitter edges, compiler references, Jedi references, CodeQL paths, Joern slices, search matches, and inferred graph relationships have different semantics and confidence.

## Decision

Use a common orchestration envelope but preserve raw provider artifacts and evidence type. Do not coerce all outputs into one undifferentiated graph.

## Consequences

- Consumers can distinguish heuristic, extracted, compiler-derived, and semantic-flow evidence.
- Cross-provider reconciliation is more verbose but more trustworthy.
- Provider replacement does not require changing the entire orchestration contract.
