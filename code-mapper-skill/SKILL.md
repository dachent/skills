---
name: code-mapper-skill
description: Maps import graphs and call-site references across a Python codebase (grimp for module-level import/dependency graphs, jedi for symbol-level call-site references) so you can see what depends on a file/function/class before changing it. Use when the user asks what breaks if they change, refactor, or delete a function or module; wants to find all callers, usages, or references of a symbol; wants a dependency/import map, blast-radius report, or impact analysis before editing unfamiliar Python code; or wants to know what else touches a module before they change it. Works on a local path or a GitHub/GitLab URL. Trigger phrases include blast radius, impact analysis, who calls/imports/uses this, find all callers/usages/references, map dependencies, is it safe to edit this.
---

# code-mapper-skill

Python-only. Two static-analysis engines, both offline, both work on modern syntax:

- **grimp** — module-level import graph. "Downstream" = what imports this module
  (blast radius — what could break). "Upstream" = what this module imports.
- **jedi** — symbol-level references. Finds every call site of a specific
  function/class across the project. Static analysis: it will miss fully dynamic
  dispatch (`getattr(obj, name)()`-style calls) — a known limitation, not a bug.

All scripts live in `scripts/` and are run with `python scripts/<name>.py ...` from
the `code-mapper-skill` directory, using whatever `python`/`pip` is ambient on `PATH` —
no venv, no isolated install. `blast_radius.py` calls `bootstrap_env.py`
implicitly on every run; the other scripts assume grimp/jedi are already
importable (run `bootstrap_env.py` once yourself first if calling them directly).

## Commands

**Bootstrap** (idempotent — installs pinned grimp/jedi via `pip install -r
requirements.txt` into the ambient environment, only if `import grimp`/`import
jedi` doesn't already work):
```
python scripts/bootstrap_env.py
```

**One-shot blast radius report** (the one you usually want):
```
python scripts/blast_radius.py <target-path-or-git-url> <file.py> [--function NAME] [--package NAME] [--subdir DIR]
```
- `target` — a local directory (the package dir itself, e.g. `...\code\src`), or a
  git URL (github.com/gitlab.com/self-hosted) — clones via the centralized git
  tooling into `C:\Dev\analysis-clones\`.
- `file.py` — path relative to the package dir, e.g. `b.py` or `sub/mod.py`.
- `--function NAME` — also find every call site of this function/class (defined in
  `file.py`) across the whole project.
- `--subdir DIR` — if `target` isn't the package dir itself (e.g. a freshly cloned
  repo where the package lives under `src/`), point at it here.
- `--package NAME` — dotted package name, default is the package dir's folder name.

Prints the merged markdown report to stdout and saves a copy under
`<repo>/.dep-map-cache/<target>-<hash>/reports/`.

**Narrower module-level queries** (import graph only, no jedi):
```
python scripts/query_imports.py <target-path> --module DOTTED.NAME [--direction upstream|downstream|both] [--find-cycles] [--shortest-chain OTHER.MODULE]
```

**Narrower symbol-level query** (jedi only, no import graph):
```
python scripts/find_references.py <target-path> --symbol MODULE.QUALNAME
```
e.g. `--symbol src.branch_residual.scrub_patient_name`.

**Just build/refresh the cached import graph**:
```
python scripts/build_graph.py <target-path> [--package NAME]
```

## Write-location guardrail

Every write lands in exactly one of: `code-mapper-skill/` itself (source), this
repo's `.dep-map-cache/` (graph cache + reports, gitignored), `C:\Dev\
bootstrap-state\code-mapper-skill-jedi-cache` (jedi's own parse cache — kept off OneDrive on purpose,
see `references/engine-notes.md`; grimp/jedi themselves install into the
ambient Python environment via normal `pip`, wherever that already is), or
`C:\Dev\analysis-clones\` (only if a git URL target is used). **Never** the
target codebase being analyzed — both engines are pure static analysis, no
execution, no `__pycache__` side effects in the target.

## Known limitations

- Python-only. A non-Python target needs a different engine entirely (this is
  intentional — no multi-language plugin layer here, YAGNI until it's needed).
- jedi's `get_references` is static; dynamic dispatch (`getattr`) won't be found.
- grimp has no single "list every cycle" call — `query_imports.py --find-cycles`
  runs a small hand-rolled Tarjan's SCC pass instead (see `scripts/_graph.py`).
