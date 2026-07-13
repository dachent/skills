# ADR-0002: The Router Owns Persistent-Graph Freshness

- Status: accepted
- Date: 2026-07-12

## Context

A graph may exist but describe an older commit, branch, root, or semantic corpus. Provider-specific hooks do not prove universal freshness. `code-mapper-skill` often receives an exact target and does not need graph discovery.

## Decision

The router evaluates persistent-graph freshness only when graph-backed retrieval is relevant. `code-mapper-skill` does not check for, query, or refresh Graphify independently.

## Consequences

- The direct mapper path avoids unnecessary graph I/O and process startup.
- Freshness policy remains centralized.
- The mapper may accept generic selection provenance but remains behaviorally independent.
- Graph-backed answers require explicit freshness state and warnings.
