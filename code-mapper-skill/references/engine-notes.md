# Engine notes

## Versions

`grimp==3.15`, `jedi==0.20.0` (pulls in `parso<0.9.0,>=0.8.6`, resolved to
`parso==0.8.7`). Pinned in `scripts/requirements.txt`. Confirmed installable as
win_amd64/py2.py3 wheels against the pyenv-win 3.10.5 interpreter on this machine.

Installed ambient (plain `pip install grimp` / `pip install jedi`, into
`C:\Tools\pyenv-win\versions\3.10.5\lib\site-packages`) rather than via an
isolated `--target` directory. Originally this used a `pip install --target
C:\Dev\bootstrap-state\code-mapper-skill-pkgs` install with a `sys.path` shim in every
script, to avoid touching the ambient interpreter -- dropped once the packages
were installed ambient directly, since maintaining an isolated copy alongside
an ambient one would just be two sources of truth for the same two packages.
`bootstrap_env.py` now just checks `import grimp`/`import jedi` succeed and
`pip install`s into the ambient environment if not.

## grimp API (confirmed against installed 3.15, not from memory)

`grimp.build_graph(package_name, *more_names, include_external_packages=False,
exclude_type_checking_imports=False, cache_dir=...)` returns an `ImportGraph`.

Semantics that are easy to get backwards:
- `find_upstream_modules(M)` = modules `M` imports (its dependencies).
- `find_downstream_modules(M)` = modules that import `M` (its dependents — this is
  blast radius, what could break if you change `M`).
- No built-in "list every cycle in the graph" call. `_graph.find_cycles()` does a
  hand-rolled Tarjan's SCC over `find_modules_directly_imported_by()` adjacency
  instead. Recursive implementation — fine at the scale this tool targets
  (dozens-to-low-hundreds of modules), would need converting to iterative if ever
  pointed at something with import chains thousands of modules deep.

## jedi gotcha: cache path length on Windows

`jedi.settings.cache_directory` controls parso's on-disk parse cache. Parso's
cache filenames are a double SHA-256 hash: `<64chars>-<64chars>.pkl` — ~133
characters just for the filename. Under a deeply nested OneDrive path (this
repo's actual path is ~90 characters on its own), the combined path exceeded
Windows' 260-char `MAX_PATH`, and `open(path, 'wb')` failed with
`FileNotFoundError` even though the parent directory existed and a plain `touch`
in the same directory worked fine — the classic MAX_PATH failure mode disguises
itself as ENOENT rather than a clear "path too long" error.

Fix applied: `JEDI_CACHE_DIR` in `_paths.py` points at
`C:\Dev\bootstrap-state\code-mapper-skill-jedi-cache` (short, off OneDrive) instead of
anywhere under this repo. If this ever needs to move again, keep the total path
budget in mind: root + `CPython-XXX-YY\` + ~133-char filename must stay under 260
(or enable Windows long-path support / use a `\\?\` prefix, but relocating is
simpler and also keeps large caches off the sync-prone OneDrive folder, same
rationale as the pip package install location).

## jedi API (confirmed against installed 0.20.0)

`jedi.Project(path, ...)` — set to the package's *parent* directory so cross-file
reference search can see sibling modules.
`jedi.Script(path=..., project=...).get_references(line, column)` — `line` is
1-indexed, `column` is 0-indexed, pointing at any character of the identifier.
Returns `Name` objects; filter out `r.is_definition()` to get only call sites, not
the definition itself.

## Fast relationship scanner

`_relationships.py` uses only the Python standard library. It scans Python ASTs and a bounded set of contract/catalog filename patterns, skips VCS/dependency/build/cache directories, and does not import target modules.

The cache has two levels:

1. per-file results keyed by kind, size, mtime, and SHA-256 content hash;
2. an aggregate graph fast path returned when the candidate set and file metadata are unchanged.

The warm path still stats candidate files so edits are detected, but it does not reconstruct or rewrite unchanged JSON outputs. This reduced the direct warm scan of 608 candidate files from about 149 ms to about 70 ms in the implementation benchmark.

The YAML support is intentionally dependency-free and targeted. It recognizes common OpenAPI, AsyncAPI, and Backstage indentation/list patterns. It does not claim to be a general YAML implementation.

## OpenLineage output

The scanner emits design-time `JobEvent` objects rather than runtime `RunEvent` objects. Each event contains `eventTime`, `producer`, `schemaURL`, `job`, `inputs`, and `outputs`, and intentionally has no `run` field. The schema URL is `https://openlineage.io/spec/2-0-2/OpenLineage.json`.

## Optional CodeQL boundary

`codeql_local_flow.py` is an explicit wrapper over an existing local CodeQL database. The default scanner never imports, installs, downloads, or invokes CodeQL. The bundled query uses CodeQL's Python modular local-data-flow API and common API graph nodes for file/data access arguments.
