---
name: code-mapper-skill
description: Maps a local Python repository with a fast standard-library AST pass and, only when explicitly requested, a CodeQL local value/taint-flow pass. Use for dependency maps, callers, artifacts, SQL tables, configuration, endpoints, events, contracts, and input-to-sink tracing.
---

# Code mapper

One command, one graph format, two explicit depths:

```text
python scripts/code_mapper.py <local-repository>
python scripts/code_mapper.py <local-repository> --deep
```

The default command performs a read-only standard-library AST and contract scan. `--deep` explicitly builds or reuses a local Python CodeQL database and adds local value/taint-flow edges.

## Interface

```text
python scripts/code_mapper.py TARGET [--deep] [--rebuild] [--codeql PATH] [--output FILE]
```

- `TARGET` must be a local directory. Clone remote repositories before invoking the skill.
- `--deep` is explicit. There is no automatic trigger policy.
- `--rebuild` discards the cached CodeQL database.
- `--codeql` selects an executable or CodeQL installation directory.
- `--output` writes the single JSON graph to a file; otherwise JSON is printed to stdout.

## Behavior

The fast pass always runs and reports:

- module imports;
- definitions and call edges;
- file, table, model, configuration, HTTP, event, and subprocess relationships;
- OpenAPI, AsyncAPI, GraphQL, Protobuf, Avro, and basic Backstage contract records.

The deep pass:

- requires CodeQL 2.16.4 or newer;
- creates Python databases with `--build-mode=none`;
- stores databases outside the target repository;
- reuses a database only when the Python source fingerprint and CodeQL version match;
- runs local value flow and local taint tracking;
- fails visibly if CodeQL is missing, the database build fails, or the query fails.

There are no compatibility modes, implicit fallbacks, heuristic scores, budget matrices, dependency installers, git-cloning helpers, Markdown renderers, or legacy entrypoints.
