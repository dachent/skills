---
name: code-mapper-skill
description: Maps Python imports, symbol references, artifact use, contracts, catalog relationships, OpenLineage datasets, and selectively triggered CodeQL local value/taint flow. Use for dependency maps, callers, inputs/outputs, APIs/schemas, Backstage relationships, blast radius, and semantic tracing. Works on a local path or Git URL.
---

# code-mapper-skill

The mapper combines:

- **Grimp:** module imports, transitive blast radius, and cycles.
- **Jedi:** references for a requested function or class.
- **AST scanner:** files, tables, models, configuration, HTTP, events, processes, and CodeQL trigger evidence.
- **Contract parsers:** OpenAPI/Swagger, AsyncAPI, GraphQL, Protobuf, JSON Schema, Avro, Pact, and Backstage.
- **OpenLineage-compatible output:** static input/output datasets.
- **CodeQL:** targeted local value flow and local taint flow when policy selects it.

The target repository is analyzed statically. Target modules are not imported or executed. CodeQL is never installed automatically. Python database creation requires CodeQL 2.16.4 or newer and always uses `--build-mode=none`.

## Command

```text
python scripts/blast_radius.py <target> <file.py> \
  [--function NAME] [--package NAME] [--subdir DIR] \
  [--codeql off|existing|auto|build] \
  [--codeql-intent mapping|value-flow|security|deep] \
  [--codeql-max-build-seconds N] \
  [--codeql-max-db-mb N] \
  [--codeql-max-query-seconds N]
```

This is the only mapper entrypoint. It emits one UTF-8 JSON graph to stdout and writes the same graph to `code-map.json` under the mapper cache. OpenLineage events and internal caches are written beside it.

## CodeQL modes

| Mode | Behavior |
| --- | --- |
| `off` | Never inspect or invoke CodeQL. |
| `existing` | Default. Use current results or a current database; never build. |
| `auto` | Build only when semantic need, expected reuse, version safety, and configured budgets pass. |
| `build` | Explicitly request database build and query, subject to the safety and budget gates. |

Repository size alone never triggers a build. Query value and database-build value are scored separately. Semantic triggers include unresolved or transformed sink arguments, parameters reaching sinks, ambiguous file modes, dynamic SQL, unresolved configuration, complex sink functions, high-value unresolved sinks, and explicit semantic intent.

Default budgets are 60 seconds for database creation, 1 GB for database size, and 5 seconds for a query. Missing CodeQL, unsupported versions, failures, and timeouts preserve the Grimp/Jedi/AST/contract map and are recorded in the JSON graph.

## Outputs

The graph includes:

- structural import dependencies and cycles;
- symbol references for `--function`;
- artifact, API, event, model, process, and contract edges;
- contract and Backstage records;
- OpenLineage event count;
- CodeQL decision, build/query diagnostics, and semantic edges;
- source fingerprints, cache statistics, and scanner errors.

## Testing

```text
python -m unittest -v smoke_test test_codeql_policy test_codeql_runtime test_codeql_cli
python scripts/benchmark_codeql_overhead.py --runs 15
python -m unittest -v test_codeql_live
```

The live test skips when CodeQL is absent. CI installs the official CLI and performs database creation, query compilation/execution, BQRS decoding, and semantic-edge assertions.

See `references/codeql-adversarial-review.md`, `references/codeql-verification.md`, and `references/codeql-benchmark-results.md`.
