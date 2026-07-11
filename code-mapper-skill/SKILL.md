---
name: code-mapper-skill
description: Maps Python imports, symbol references, artifact use, contracts, catalog relationships, and selectively triggered local value/taint flow for blast-radius and input-to-sink analysis. Use for dependency maps, callers, inputs/outputs, APIs/schemas, Backstage relationships, and semantic tracing. Works on a local path or Git URL.
---

# code-mapper-skill

Local, read-only Python analysis:

- **grimp:** module imports, transitive blast radius, and cycles.
- **jedi:** references for a requested function/class.
- **AST scanner:** files, tables, models, config, HTTP, events, processes, and semantic-trigger evidence.
- **contract parsers:** OpenAPI/Swagger, AsyncAPI, GraphQL, Protobuf, JSON Schema, Avro, Pact, and Backstage.
- **OpenLineage-compatible output:** static job inputs/outputs.
- **optional CodeQL:** AST-targeted local value and local taint flow.

The skill never installs/downloads CodeQL, imports target modules, or executes target code. Python database creation requires CodeQL 2.16.4+ and `--build-mode=none`.

## Main command

```text
python scripts/blast_radius.py <target> <file.py> \
  [--function NAME] [--package NAME] [--subdir DIR] \
  [--codeql off|existing|auto|build] \
  [--codeql-intent mapping|value-flow|security|deep] \
  [--skip-relationships]
```

Existing arguments remain valid. `--skip-relationships` restores the original Grimp/Jedi-only path.

## Relationship graph

```text
python scripts/scan_relationships.py <target> [--package NAME] [--subdir DIR] \
  [--codeql off|existing|auto|build] \
  [--codeql-intent mapping|value-flow|security|deep]
```

Outputs under `.dep-map-cache/`: relationship graph/cache, OpenLineage events, reports, and optional CodeQL database/results/history.

## CodeQL modes

| Mode | Behavior |
| --- | --- |
| `off` | Never inspect or invoke CodeQL. |
| `existing` | Default. Use current results/database; never build. Without either, do not probe the CLI. |
| `auto` | Build only when semantic need, reuse, safe version, and budgets pass. |
| `build` | Explicit build/query request, still constrained by safety and budgets. |

Repository size alone never builds. Query and database-build scores are separate.

Semantic triggers include unresolved/transformed sink arguments, parameters reaching sinks, ambiguous file modes, dynamic SQL, unresolved config, complex sink functions, high-value unresolved sinks, and explicit semantic intent.

Build selection additionally considers parameterized high-value sinks, repeated analyses, existing CodeQL configuration, temporary-repository status, prior failures/invalidation, projected time, and projected storage.

```text
--codeql-max-build-seconds N
--codeql-max-db-mb N
--codeql-max-query-seconds N
```

Defaults: 60 seconds, 1 GB, and 5 seconds. Failures/timeouts preserve the base map.

## Engine responsibilities

| Engine | Purpose |
| --- | --- |
| Grimp | structural module dependencies |
| Jedi | arbitrary symbol references |
| AST/contracts | fast discovery, literals/inference, contracts, and CodeQL targeting |
| CodeQL local flow | value-preserving propagation within one callable |
| CodeQL local taint | transformed influence within one callable |

CodeQL augments rather than replaces the other engines. Global flow is out of scope.

## Manual query

```text
python scripts/codeql_local_flow.py <existing-database> [--output results.csv]
```

## Testing

```text
python scripts/smoke_test.py
python -m unittest -v test_codeql_policy test_codeql_runtime test_codeql_cli test_codeql_live
python scripts/benchmark_codeql_overhead.py --runs 15
```

The live test skips without CodeQL; CI installs the official CLI and runs it.

See `references/codeql-adversarial-review.md`, `references/codeql-verification.md`, and `references/codeql-benchmark-results.md`.

## Compatibility and writes

The interface remains ordinary Python CLI plus UTF-8 Markdown/JSON/CSV, with no Claude-, Codex-, Hermes-, or MCP-specific dependency. Writes remain limited to the skill, `.dep-map-cache`, existing Grimp/Jedi cache locations, and the centralized clone directory. The target repository remains read-only.
