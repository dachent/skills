---
name: code-mapper-skill
description: Maps import graphs, symbol references, local artifact use, contracts, and catalog relationships across a Python codebase so you can see what depends on a file/function/class before changing it. Use when the user asks what breaks if they change, refactor, or delete a function or module; wants callers, usages, references, input/output artifacts, API/schema contracts, Backstage relationships, a dependency map, blast-radius report, or impact analysis before editing unfamiliar Python code. Works on a local path or a GitHub/GitLab URL.
---

# code-mapper-skill

Python-only, offline, static analysis. The default path remains local and fast:

- **grimp** — module-level import graph. Downstream is blast radius; upstream is dependencies.
- **jedi** — symbol-level references for a requested function/class.
- **standard-library AST scanner** — file, table, model, config, endpoint, and event use.
- **contract parsers** — OpenAPI/Swagger, AsyncAPI, GraphQL, Protobuf, JSON Schema, Avro, and Pact files.
- **Backstage parser** — catalog entities and `providesApis`, `consumesApis`, `dependsOn`, ownership, system/domain, and referenced definitions.
- **OpenLineage-compatible static output** — design-time `JobEvent` records for detected input/output datasets.

The default scanner does not execute target code, import target modules, contact a service, or require a lineage server. It uses a per-file content-hash cache and a metadata fast path. CodeQL is explicit-only and is never installed or invoked by the normal commands.

All scripts live in `scripts/` and run with the ambient `python`/`pip` on `PATH`. `blast_radius.py` calls `bootstrap_env.py`; the relationship scanner itself has no third-party dependencies.

## Commands

### Bootstrap

```text
python scripts/bootstrap_env.py
```

Installs the pinned `grimp` and `jedi` versions only when they are not already importable.

### One-shot blast-radius report

```text
python scripts/blast_radius.py <target-path-or-git-url> <file.py> [--function NAME] [--package NAME] [--subdir DIR] [--skip-relationships]
```

- `target` — local directory or git URL.
- `file.py` — path relative to the package directory.
- `--function NAME` — add Jedi references for the named function/class.
- `--subdir DIR` — package directory relative to the repository root.
- `--package NAME` — dotted package name; defaults to the package directory name.
- `--skip-relationships` — diagnostic escape hatch that preserves the original Grimp/Jedi-only path.

The command prints the existing import/reference report plus additive artifact/contract sections. It writes reports and graph outputs under `.dep-map-cache/`, never inside the target repository.

### Build only the artifact/contract/catalog graph

```text
python scripts/scan_relationships.py <target-path-or-git-url> [--package NAME] [--subdir DIR]
```

Outputs:

- `relationships.json` — evidence-backed relationship edges and contract/catalog records.
- `openlineage-job-events.json` — OpenLineage-compatible static `JobEvent` objects.
- `relationship-cache.json` — per-file cache keyed by size, mtime, and SHA-256 content hash.

Relationship types include:

```text
READS_FILE, WRITES_FILE, READS_TABLE, WRITES_TABLE,
LOADS_MODEL, SAVES_MODEL, READS_CONFIG,
IMPLEMENTS_ENDPOINT, CONSUMES_ENDPOINT,
PRODUCES_EVENT, CONSUMES_EVENT,
DEFINES_ENDPOINT, DEFINES_SCHEMA, DEFINES_RPC,
PROVIDES_API, CONSUMES_API, DEPENDS_ON, OWNED_BY, PART_OF
```

Every edge includes source, target, relationship, confidence, file, line, symbol where available, and extractor.

### Existing narrow queries

```text
python scripts/query_imports.py <target-path> --module DOTTED.NAME [--direction upstream|downstream|both] [--find-cycles] [--shortest-chain OTHER.MODULE]
python scripts/find_references.py <target-path> --symbol MODULE.QUALNAME
python scripts/build_graph.py <target-path> [--package NAME]
```

### Optional CodeQL local flow

```text
python scripts/codeql_local_flow.py <existing-codeql-database> [--output results.csv]
```

This command is manual-only. It requires a locally installed `codeql` CLI and an existing local Python CodeQL database. It does not download CodeQL, create a database, use the network, or run during `blast_radius.py`.

Use it only when intra-function value flow into common file/data access arguments is materially useful and the normal AST/Jedi map is insufficient.

## Performance validation

Run the smoke suite:

```text
python scripts/smoke_test.py
```

Compare a baseline checkout and candidate checkout with full CLI subprocess timing:

```text
python scripts/benchmark_runtime.py <baseline-skill-root> <candidate-skill-root> <target> <file.py> \
  --subdir <package-dir> --package <package> --runs 7 --warmups 2 \
  --max-median-delta-percent 10 --max-median-delta-seconds 0.25
```

Add `--cold` to clear each checkout's code-mapper caches before every run. See `references/benchmark-results.md` for the implementation benchmark.

## Agent/runtime compatibility

The command contract is deliberately shell- and agent-neutral:

- existing positional arguments and flags are unchanged;
- stdout remains Markdown plus the existing saved-report line;
- new report sections are additive;
- outputs are ordinary UTF-8 JSON/Markdown files;
- no MCP, Claude-, Codex-, or Hermes-specific API is required;
- no target code is executed or imported;
- no network is used for local targets;
- CodeQL absence cannot affect the default path.

Claude Code, Codex, and Hermes can continue invoking the scripts as ordinary local Python commands. `--skip-relationships` provides a compatibility fallback if a downstream parser requires byte-for-byte legacy report structure.

## Write-location guardrail

Writes are limited to:

- this skill directory when its source is being edited;
- the repository's `.dep-map-cache/` for reports, relationship graphs, and caches;
- `C:\Dev\bootstrap-state\code-mapper-skill-jedi-cache`;
- `C:\Dev\bootstrap-state\code-mapper-skill-grimp-cache`;
- `C:\Dev\analysis-clones\` when a git URL is explicitly supplied.

The target repository remains read-only.

## Known limitations

- Python-only for code analysis; contract files may describe non-Python interfaces.
- Static analysis cannot fully resolve reflection, dynamic dispatch, generated paths, or runtime-selected dependencies.
- Inferred paths use placeholders such as `${name}` and are marked `inferred`.
- The dependency-free YAML readers intentionally support common OpenAPI/AsyncAPI/Backstage structures, not every YAML feature or custom tag.
- CodeQL local flow is intra-function and requires a separately prepared local database.
