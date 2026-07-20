# Code Intelligence Architecture

## Decision summary

`code-intelligence` is a thin control plane, not a new analysis engine. It solves routing and freshness problems across a deliberately small set of existing capabilities.

## Active system model

```text
User or coding agent
        |
        v
code-intelligence
  - explicit intent classification
  - lightweight Graphify freshness preflight
  - deterministic route selection
  - minimal evidence metadata
        |
        +--> direct source/search/tests
        +--> Graphify for fresh broad discovery
        +--> code-mapper-skill for Python analysis
        |      +--> selective CodeQL enrichment when triggered
```

## Why these components remain

### Direct source and tests

They are the fallback and final authority. No index or analyzer is assumed complete or current.

### Graphify

Graphify has a differentiated role for repeated broad discovery and mixed code/document/media projects. It is used only when an existing graph is relevant and fresh.

### `code-mapper-skill`

The mapper has a distinct Python-specific combination of import graphs, references, artifact and contract extraction, API/catalog relationships, OpenLineage-compatible output, and selective CodeQL enrichment.

### Selective CodeQL inside the mapper

CodeQL remains because syntax and import graphs cannot establish all value-flow or taint relationships. It is not promoted to a new standalone router integration in the MVP.

## Deferred or rejected

- Codebase-Memory: benchmark-only replacement candidate for Graphify on code-only work.
- Serena: dropped; exact semantic editing is not an MVP router responsibility.
- Joern/codebadger: dropped; too heavy and security-specialized for current recurring needs.
- SCIP/Sourcegraph: deferred until enterprise cross-repository precision is demonstrated.
- Semgrep: separate rule scanner, not a repository-intelligence route.
- Aider-style map: redundant with Graphify and direct exploration for the current scope.
- Generic LSP integration: host or IDE concern, not implemented here.

## Execution paths

### Known Python target

```text
known file or symbol
    -> no Graphify I/O
    -> code-mapper-skill
    -> inspect source locations
    -> verify source and tests
```

### Broad discovery

```text
unknown implementation location
    -> inspect Graphify freshness metadata
    -> fresh Graphify graph, or direct source fallback
    -> identify candidate files and symbols
    -> code-mapper for Python candidates when useful
    -> verify source and tests
```

### Python security/value flow

```text
security or value-flow question
    -> code-mapper-skill
    -> selective CodeQL only when available and triggered
    -> inspect paths and source
    -> test or reproduce
```

## Operational principles

1. Do not pay index cost for a known target.
2. Do not infer freshness from file existence.
3. Do not add a provider before measurable value is demonstrated.
4. Do not auto-build or auto-refresh an index.
5. Do not let one provider failure block direct source analysis.
6. Do not flatten evidence types into an anonymous graph.
7. Do not edit code based solely on analyzer output.
8. Do not report completion until required CI is green.
