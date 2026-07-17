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
    cli.py                    # `validate` and `dry-run` subcommands
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

The only dependency is `jsonschema`, because there is no JSON-Schema
validator in the Python standard library and RFC 0001 requires the contract
to be JSON-Schema-backed.

## Using the CLI

Both subcommands work with no Excel installed.

```
python xlsx-win/v2/control_plane/cli.py validate  <manifest.json>
python xlsx-win/v2/control_plane/cli.py dry-run   <manifest.json>
```

`validate` schema-checks the manifest and prints `{"valid": true}` or
`{"valid": false, "error": {code, message, details}}` (exit code 1 on
failure). `dry-run` does the same schema check, then prints the state
sequence the job would traverse -- including, on a schema failure inside one
of the steps, a `details.json_path` pointing at the offending step.

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
