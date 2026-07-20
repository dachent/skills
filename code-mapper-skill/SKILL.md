---
name: code-mapper-skill
description: Generate deterministic Python import, reference, artifact, contract, catalog, OpenLineage, and explicitly authorized local CodeQL maps. Use for explicit Python blast-radius, callers, inputs/outputs, APIs/schemas, Backstage relationships, lineage, or local value/taint evidence; do not use for ordinary code search, broad repository exploration, or simple edits.
---

# code-mapper-skill

The mapper combines:

- **Grimp:** module imports, transitive blast radius, and cycles.
- **Jedi:** references for a requested function or class.
- **AST scanner:** files, tables, models, configuration, HTTP, events, processes, and CodeQL trigger evidence.
- **Contract parsers:** OpenAPI/Swagger, AsyncAPI, GraphQL, Protobuf, JSON Schema, Avro, Pact, and Backstage.
- **OpenLineage-compatible output:** static input/output datasets.
- **CodeQL:** targeted local value flow and local taint flow when policy selects it.

Analyze the target repository statically. Do not import or execute target modules. Never install dependencies, clone or refresh repositories, download CodeQL packs, or select a persistent cache location automatically.

Require an explicit work root. Use the active session's `.codex-bootstrap\code-mapper` for Codex or `.claude-bootstrap\code-mapper` for Claude Code. Keep every report, parser cache, and optional CodeQL artifact below that root. Use a local target path from the harness-approved Git workflow; refuse Git URLs.

## Command

```text
python scripts/blast_radius.py <local-target> <file.py> --work-root <session-bootstrap> \
  [--function NAME] [--package NAME] [--subdir DIR] \
  [--codeql off|existing|auto|build] \
  [--codeql-intent mapping|value-flow|security|deep] \
  [--codeql-max-build-seconds N] \
  [--codeql-max-db-mb N] \
  [--codeql-max-query-seconds N] \
  [--allow-codeql-write]
```

Use this as the only mapper entrypoint. It emits one UTF-8 JSON graph to stdout and writes the same graph to `code-map.json` below the explicit work root. OpenLineage events and internal caches are written there too.

Run `python scripts/bootstrap_env.py` as a read-only preflight. Provision the exact pins in `scripts/requirements.txt` through an explicitly approved `C:\Tools\code-mapper` runtime or session-local virtual environment. The preflight never runs `pip`.

## CodeQL modes

| Mode | Behavior |
| --- | --- |
| `off` | Never inspect or invoke CodeQL. |
| `existing` | Default. Read current cached results only; never build, query, download, or write without `--allow-codeql-write`. |
| `auto` | Require `--allow-codeql-write`; never download a query pack. |
| `build` | Require `--allow-codeql-write` and a pre-provisioned local pack lock. |

Repository size alone never triggers a build. Query value and database-build value are scored separately. Semantic triggers include unresolved or transformed sink arguments, parameters reaching sinks, ambiguous file modes, dynamic SQL, unresolved configuration, complex sink functions, high-value unresolved sinks, and explicit semantic intent.

Obtain explicit user authorization before adding `--allow-codeql-write`. Database creation requires CodeQL 2.16.4 or newer and uses `--build-mode=none`. Default budgets are 60 seconds for database creation, 1 GB for database size, and 5 seconds for a query. Missing CodeQL, absent setup, unsupported versions, failures, and timeouts preserve the Grimp/Jedi/AST/contract map.

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
python -m unittest -v smoke_test test_safety test_codeql_policy test_codeql_runtime test_codeql_cli
python scripts/benchmark_codeql_overhead.py --runs 15
python -m unittest -v test_codeql_live
```

The live test skips when CodeQL is absent. CI installs the official CLI and performs database creation, query compilation/execution, BQRS decoding, and semantic-edge assertions.

See `references/codeql-adversarial-review.md`, `references/codeql-verification.md`, and `references/codeql-benchmark-results.md`.
