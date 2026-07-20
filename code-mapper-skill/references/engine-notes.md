# Engine notes

## Runtime contract

Use `grimp==3.15` and `jedi==0.20.0`, pinned in `scripts/requirements.txt`. Run `scripts/bootstrap_env.py` only as a read-only version preflight. It never installs or upgrades packages.

For a reusable Windows installation, provision a dedicated runtime under `C:\Tools\code-mapper`. For a one-session runtime, use the active session's `.codex-bootstrap\code-mapper` or `.claude-bootstrap\code-mapper`. Do not install into an ambient interpreter.

Require `--work-root` or `CODE_MAPPER_WORK_ROOT`. Grimp, Jedi, relationship, OpenLineage, report, and CodeQL state must remain below that root. A short work root also avoids Jedi/parso path-length failures on Windows.

Accept local targets only. The mapper does not clone, fetch, pull, or update repositories. Resolve Git URLs through the harness-approved centralized-Git workflow before invoking the mapper.

## Grimp

`grimp.build_graph(package_name, *more_names, include_external_packages=False, exclude_type_checking_imports=False, cache_dir=...)` returns an `ImportGraph`.

- `find_upstream_modules(M)` returns modules imported by `M`.
- `find_downstream_modules(M)` returns modules that import `M`, which is the blast radius.
- `_graph.find_cycles()` uses Tarjan's strongly connected components algorithm.

## Jedi

Set `jedi.settings.cache_directory` below the explicit work root. Build `jedi.Project` from the package parent so reference search sees sibling modules. Jedi line positions are one-based; columns are zero-based.

## Relationship scanner and OpenLineage

`_relationships.py` uses the Python standard library. It scans Python ASTs and bounded contract/catalog filename patterns, skips VCS/dependency/build/cache directories, and never imports target modules.

The scanner emits design-time OpenLineage `JobEvent` objects with `eventTime`, `producer`, `schemaURL`, `job`, `inputs`, and `outputs`; it intentionally emits no runtime `run` field.

## CodeQL boundary

CodeQL is optional. Default `existing` mode performs no CodeQL write or subprocess query. Require `--allow-codeql-write` for database, query, result, or history writes. The mapper never runs `codeql pack install`; provision a query-pack lock and dependencies through a separately approved setup action.
