# Code Intelligence Architecture

## Decision summary

`code-intelligence` is a control plane, not a new analysis engine. It routes questions to independent providers, evaluates freshness and cost, combines evidence without erasing provenance, and requires source-level verification before material edits.

## System model

```text
User or coding agent
        |
        v
code-intelligence control plane
  - intent classification
  - capability and freshness preflight
  - cost and risk policy
  - provider selection
  - evidence normalization
        |
        +--> direct source/search/tests
        +--> persistent graph provider
        |      Graphify or Codebase-Memory
        +--> precise semantic navigation
        |      LSP, Serena, SCIP, Sourcegraph
        +--> Python precision provider
        |      code-mapper-skill
        +--> semantic flow/security
        |      CodeQL, Joern/codebadger, Semgrep
        +--> durable planning map
               repo-map-codex
```

## Provider classes

### Discovery and repository memory

Use persistent graphs for broad questions, architecture, candidate-file discovery, cross-service relationships, and repeated work. Graphify is the initial optional provider because it supports code plus documents and media. Codebase-Memory is a high-priority alternative for code-only work because it combines persistent graph retrieval, MCP, hybrid semantic resolution, incremental indexing, and local operation.

### Exact symbol semantics

Use compiler, language-server, SCIP, or IDE-backed providers when correctness depends on definitions, references, implementations, type hierarchy, or safe refactoring. Tree-sitter graphs are useful discovery indexes but are not substitutes for compiler-accurate semantics.

### Specialized Python analysis

Keep `code-mapper-skill` independent. It remains responsible for Grimp import graphs, Jedi references, custom Python AST artifact extraction, contracts, OpenLineage-compatible records, and selective local CodeQL enrichment.

### Semantic flow and security

Use CodeQL or Joern/codebadger when the request depends on interprocedural data flow, taint, program slicing, or security reasoning. The router must distinguish local from global analysis and report scope explicitly.

### Direct source and tests

Source, build metadata, contracts, and tests are the final authority. Every provider can be stale, incomplete, language-limited, or heuristically wrong.

## Execution paths

### Exact-target fast path

```text
known Python file or symbol
    -> route without loading graph data
    -> code-mapper-skill
    -> inspect returned source locations
    -> verify source and tests
```

### Discovery-to-precision path

```text
unknown implementation location
    -> check graph availability and freshness
    -> query graph or explore source directly
    -> identify candidate files and symbols
    -> invoke precise provider
    -> verify source and tests
```

### Security path

```text
security or data-flow question
    -> identify language and source/sink scope
    -> use CodeQL or Joern/codebadger when available
    -> use focused queries and explicit budgets
    -> inspect paths and sanitizers in source
    -> run tests or reproducer
```

## Evidence model

Never flatten all results into an anonymous graph. Preserve:

- provider and version;
- extraction or inference method;
- repository root and revision;
- freshness state;
- source locations;
- query and analysis scope;
- latency and resource cost;
- warnings, failures, and fallbacks.

## Operational principles

1. Do not pay index cost for a known target.
2. Do not infer freshness from file existence.
3. Do not make a provider mandatory unless it is necessary for the documented route.
4. Do not silently invoke model-backed semantic extraction on private documents.
5. Do not allow one provider failure to block unrelated providers.
6. Do not call a heuristic relationship compiler-accurate.
7. Do not edit code based solely on graph output.
