# xlsx-win v2 control plane -- contract only

This directory implements issue #34: the LLM-facing job/result contract for
the xlsx-win v2 runtime, scoped to a single desktop per
[RFC 0002](../../docs/rfcs/0002-xlsx-win-v2-single-user-scope.md) (which
amends [RFC 0001](../../docs/rfcs/0001-xlsx-win-runtime-v2.md)).

## Scope

**This is contract only. Nothing here touches Excel.**

- JSON Schema for job manifests and results (`schemas/`).
- A state machine: the fixed list of states, legal transitions, and a
  terminal-state check (`control_plane/state_machine.py`).
- A normalized error taxonomy: `{code, message, details}`
  (`control_plane/errors.py`).
- A dry-run simulator that maps a job's steps to the state sequence it would
  traverse, with no Excel (`control_plane/dry_run.py`).
- A result-contract builder that computes the top-level `ok` field
  (`control_plane/result_contract.py`).
- A CLI that validates and dry-runs manifests without Excel
  (`control_plane/cli.py`).
- A thin, narrowly-scoped adapter that translates one recognized job shape
  into the legacy `refresh_excel.ps1` argument list, for migration
  (`control_plane/legacy_adapter.py`).

No module in this directory imports `pywin32`, calls Excel COM, imports
`openpyxl`, or otherwise touches a workbook file. Building the runtime that
actually drives Excel against this contract is issue **#36**, a separate,
later workstream.

## Layout

```
xlsx-win/v2/
  schemas/
    job.schema.json      # job manifest: an ordered `steps` array
    result.schema.json    # computed result: per-step outcomes + top-level `ok`
  control_plane/
    errors.py             # ContractError + the error code taxonomy
    schemas.py             # loads schemas, validates, classifies failures
    state_machine.py       # STATES, TERMINAL_STATES, can_transition, is_terminal
    dry_run.py              # simulate_transitions(job) -- no Excel
    result_contract.py      # build_result(...) -- computes `ok`
    legacy_adapter.py        # translate_refresh_and_recalc(job) -> PowerShell args
    workbook_inventory.py     # inspect_workbook(path) -- reads the OOXML package directly
    file_router.py             # choose_backend(intent, inventory) -- deterministic routing
    cli.py                    # `validate`, `dry-run`, and `route` subcommands
  tests/
    fixtures/                 # on-disk manifests used by the CLI tests
    test_*.py
  requirements.txt
```

## Job contract, in one paragraph

A job is `{schema_version, idempotency_key, steps}`. `steps` is an ordered
list; each step is one of `open`, `refresh` (a connection name list, or the
literal string `"all"`), `recalc`, `run_approved_macro`, or `save_as`. Both
the job schema and every step schema use `additionalProperties: false`, so
unknown top-level fields and unknown step types are rejected the same way.

A result is `{schema_version, run_id, idempotency_key, final_state, steps,
invariants, ok}`. `ok` is **never** a parameter you can pass in --
`result_contract.build_result()` has no `ok` argument at all. It is always
computed from whether every step succeeded and every declared invariant (if
any) passed.

## Installing dependencies

```
pip install -r xlsx-win/v2/requirements.txt
```

`jsonschema` backs the job/result contract (#34); `openpyxl` and
`xlsxwriter` are the two real backends the router (#35) chooses between --
neither is imported by `workbook_inventory.py` itself, which inspects OOXML
packages directly instead of opening them.

## Using the CLI

All three subcommands work with no Excel installed.

```
python xlsx-win/v2/control_plane/cli.py validate  <manifest.json>
python xlsx-win/v2/control_plane/cli.py dry-run   <manifest.json>
python xlsx-win/v2/control_plane/cli.py route     <workbook.xlsx> <create_new|edit_existing|convert_format>
```

`validate` schema-checks the manifest and prints `{"valid": true}` or
`{"valid": false, "error": {code, message, details}}` (exit code 1 on
failure). `dry-run` does the same schema check, then prints the state
sequence the job would traverse -- including, on a schema failure inside one
of the steps, a `details.json_path` pointing at the offending step. `route`
inspects the workbook's OOXML package and prints the resulting
`RouterDecision` (`backend`, `reason`, `explain`) as JSON.

## Running the tests

```
pip install -r xlsx-win/v2/requirements.txt
python -m pytest xlsx-win/v2/tests/
```

(Run from the repository root, or from `xlsx-win/v2/` -- `tests/conftest.py`
puts `xlsx-win/v2/` on `sys.path` either way.)

## What "validation" means here (and does not)

Per RFC 0002 decision 6: validation in this contract is bounded to
*completion evidence* (did each step report success) plus *declared
invariants* (contract-supplied assertions such as row-count minimums or
sentinel values) -- never a claim that workbook data is *correct*. This
skeleton does not implement invariant evaluation against a real workbook
(there is no workbook I/O here at all); it only defines the shape a result
carries invariants in, and computes `ok` from whatever outcomes it's given.
Evaluating invariants against a real, opened workbook is #36/#38's job.

## File-backend router (issue #35)

Also contract-adjacent, still no Excel: deterministic routing for workbook
creation, reading, and editing *before* any native Excel compute (#36).

- `control_plane/workbook_inventory.py` -- `inspect_workbook(path)` reads a
  workbook's raw OOXML package (`zipfile` + minimal namespace-agnostic XML
  parsing) and returns a `WorkbookInventory` dataclass: `exists`,
  `file_format`, `sheet_count`, and the risk flags `has_macros`, `is_signed`,
  `has_external_links`, `has_data_model`, `has_pivots`, `has_slicers`,
  `has_embedded_objects`, plus `is_classifiable` (False when an xlsx/xlsm-
  named file can't be positively identified as a well-formed OOXML package).
  It never imports openpyxl and never raises for a missing or corrupt file --
  asking openpyxl's own object model whether a workbook is safe would be
  circular, since part of the job here is deciding whether openpyxl is even
  safe to open it with.
- `control_plane/file_router.py` -- `choose_backend(intent, inventory)`
  returns a `RouterDecision` (`backend`, `reason`, `explain`) using straight
  boolean logic, no LLM judgment or heuristic scoring. `explain` names the
  exact inventory fields that drove the decision, so a decision is
  inspectable in JSON, not just a free-text reason.
- `control_plane/cli.py route <workbook> <intent>` -- runs both and prints
  the `RouterDecision` as JSON.

### Single-user descope (RFC 0002) -- what this is, and is not

RFC 0001's "File-backend routing" section lists a full matrix (XlsxWriter,
PyExcelerate, pandas/Polars, fastexcel/calamine, openpyxl, a targeted OOXML
patcher, Open XML SDK, Aspose.Cells, Path C bulk writes). RFC 0002 trims that
to what a one-person desktop deployment actually needs, without evaluating
or benchmarking the rest of the matrix up front. This issue implements
exactly three outcomes:

- **`xlsxwriter`** -- new workbook creation with no existing file to
  preserve.
- **`openpyxl`** -- editing an existing plain xlsx/xlsm with none of the
  tracked risk features.
- **`excel_required`** -- the fail-closed escape hatch for macros,
  signatures, a Data Model, pivots, slicers, embedded objects, external
  links, or any workbook this router cannot positively classify as safe.
  RFC 0001 is explicit that a successful-looking edit is not evidence a
  workbook was safe to touch outside Excel, so the router never guesses into
  openpyxl for these.

Plus two edge outcomes: **`convert_required`** for legacy binary `.xls`
under `edit_existing` (must become `.xlsx` before any Python-side edit --
this router does not perform the conversion itself; under `create_new` a
legacy `.xls` target instead fails closed to `excel_required`, since there
is no existing file for a convert-then-edit path to apply to), and
**`not_applicable`** for `.csv`/`.tsv` under *any* intent -- plain delimited
text is not an OOXML workbook, Excel adds no fidelity value over a direct
text read/write, but neither xlsxwriter (OOXML creation-only) nor openpyxl
(OOXML structure editing) is a fit for it either, so the router declines to
claim routing authority over CSV/TSV rather than guessing, for `create_new`
just as much as for `edit_existing`.

**Explicitly out of scope for #35** (per the amendment):

- PyExcelerate, Aspose.Cells, fastexcel/calamine, and Open XML SDK are not
  implemented or evaluated here.
- No benchmark corpus or fixture suite for backend comparison -- that is
  issue #39's job. The only timing comparison here is one lightweight
  xlsxwriter-vs-openpyxl sanity check for the new-workbook fast path
  (`tests/test_file_router.py::test_xlsxwriter_new_workbook_creation_is_faster_than_openpyxl`),
  not a corpus.
- pandas is out of scope for routing decisions -- it is a data-shaping tool
  the skill already uses per `SKILL.md`, not a routing target this module
  chooses between.
- The original issue's full inventory (drawings, queries/connections,
  add-in dependencies, calculation settings, edit volume/shape) is not
  detected here; only the fields the descoped routing rules actually
  consume are.

A package-diff test (`tests/test_package_diff.py`) creates a small workbook,
copies it, makes a trivial openpyxl edit on the copy, and asserts the
*meaningful* OOXML parts (worksheets, a defined name, a comment) survive the
round trip -- not a byte-identical zip, since re-serialization churn
(timestamps, calcChain, part order) is expected.

## Known gap against the original #34 acceptance criteria

The original criteria asked for "Hosted tests cover valid, invalid, unsafe,
version-mismatch, cancellation, and retry manifests." All six are covered in
`tests/`, but the **retry** coverage is necessarily narrower than a full
execution engine's idempotency guarantee: this directory has no job store,
no execution history, and no de-duplication logic (there is nothing here
that runs a job twice to dedupe against). What `tests/test_dry_run.py`
proves instead is that this contract layer is *safe to retry against*: the
same manifest always maps to the same schema-validity verdict and the same
simulated state sequence, with no hidden mutable state. Whether a
resubmitted `idempotency_key` is actually deduplicated at execution time is
an execution-engine concern that belongs to #36.
