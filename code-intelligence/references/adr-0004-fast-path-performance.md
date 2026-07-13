# ADR-0004: Protect the Exact-Target Fast Path

- Status: accepted
- Date: 2026-07-12

## Context

The mapper's measured end-to-end runtime is roughly 1.5 to 2.7 seconds in published fixtures. Loading a persistent graph can add material latency and memory use, especially when the exact file and symbol are already known.

## Decision

The router may perform only lightweight metadata checks before a direct mapper route. It must not load `graph.json`, invoke Graphify, or refresh an index on that path.

## Performance gates

- at most 75 ms median absolute overhead;
- at most 5 percent median relative overhead;
- at most 200 ms p95 absolute overhead;
- zero Graphify subprocesses and graph JSON reads.

## Consequences

Graph-based context is an explicit second-stage operation, not an invisible tax on every mapper invocation.
