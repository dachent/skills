# xlsx-win v2 control plane -- contract, validation, and policy only

This directory implements issue #34 (the LLM-facing job/result contract) and
issue #38 (workbook validation contracts, macro policy, staging, and the
audit manifest) for the xlsx-win v2 runtime, scoped to a single desktop per
[RFC 0002](../../docs/rfcs/0002-xlsx-win-v2-single-user-scope.md) (which
amends [RFC 0001](../../docs/rfcs/0001-xlsx-win-runtime-v2.md)).

## Scope

**This is contract, validation, and policy only. Nothing here drives Excel
via COM.**

- JSON Schema for job manifests, results, workbook validation contracts, and
  audit manifests (`schemas/`).
- A state machine: the fixed list of states, legal transitions, and a
  terminal-state check (`control_plane/state_machine.py`).
- A normalized error taxonomy: `{code, message, details}`
  (`control_plane/errors.py`).
- A dry-run simulator that maps a job's steps to the state sequence it would
  traverse, with no Excel (`control_plane/dry_run.py`).
- A result-contract builder that computes the top-level `ok` field
  (`control_plane/result_contract.py`).
- A workbook-validation-contract evaluator that reads a saved workbook's
  *cached* values with openpyxl and checks declared invariants against them
  (`control_plane/invariant_evaluator.py`) -- see "What validation means
  here" below.
- A macro allowlist policy: exact-match only, no wildcards
  (`control_plane/macro_policy.py`).
- Local-copy staging and atomic publish-back
  (`control_plane/staging.py`).
- An audit manifest linking a run's input/output hashes, validation
  contract, and (redacted) invariant results
  (`control_plane/audit_manifest.py`).
- A CLI that validates and dry-runs manifests, and evaluates workbook
  validation contracts (`control_plane/cli.py`).
- A thin, narrowly-scoped adapter that translates one recognized job shape
  into the legacy `refresh_excel.ps1` argument list, for migration
  (`control_plane/legacy_adapter.py`).

No module in this directory imports `pywin32` or calls Excel COM.
`invariant_evaluator.py` is the one module that reads a workbook file (with
openpyxl, read-only, cached values); everything else here is pure Python
over JSON documents and the filesystem. Building the runtime that actually
drives Excel against this contract is issue **#36**, a separate, later
workstream.

## Layout

```
xlsx-win/v2/
  schemas/
    job.schema.json                 # job manifest: an ordered `steps` array
    result.schema.json               # computed result: per-step outcomes + top-level `ok`
    validation_contract.schema.json   # sidecar per-workbook declared-invariant contract (#38)
    audit_manifest.schema.json        # audit manifest shape (#38)
  control_plane/
    errors.py             # ContractError + the error code taxonomy
    schemas.py             # loads schemas, validates, classifies failures
    state_machine.py       # STATES, TERMINAL_STATES, can_transition, is_terminal
    dry_run.py              # simulate_transitions(job) -- no Excel
    result_contract.py      # build_result(...) -- computes `ok`
    invariant_evaluator.py  # evaluate_contract(workbook_path, contract) -- #38
    macro_policy.py          # is_macro_approved(...) -- exact-match allowlist, #38
    staging.py                # stage_copy(...) / publish(...) -- #38, RFC 0002 decision 9
    audit_manifest.py          # build_audit_manifest(...) -- #38
    legacy_adapter.py        # translate_refresh_and_recalc(job) -> PowerShell args
    cli.py                    # `validate`, `dry-run`, `validate-contract` subcommands
  tests/
    fixtures/                 # on-disk manifests used by the CLI tests
    wb_fixtures.py             # shared openpyxl workbook-builder helper for tests
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

The dependencies are `jsonschema` (there is no JSON-Schema validator in the
Python standard library, and RFC 0001 requires the contract to be
JSON-Schema-backed) and `openpyxl` (used only by
`invariant_evaluator.py`, to read a saved workbook's cached values --
never to drive Excel).

## Using the CLI

All three subcommands work with no Excel installed. `validate-contract`
does read the workbook file itself (with openpyxl), but never launches
Excel or touches COM.

```
python xlsx-win/v2/control_plane/cli.py validate           <manifest.json>
python xlsx-win/v2/control_plane/cli.py dry-run            <manifest.json>
python xlsx-win/v2/control_plane/cli.py validate-contract  <workbook.xlsx> <contract.json>
```

`validate` schema-checks the manifest and prints `{"valid": true}` or
`{"valid": false, "error": {code, message, details}}` (exit code 1 on
failure). `dry-run` does the same schema check, then prints the state
sequence the job would traverse -- including, on a schema failure inside one
of the steps, a `details.json_path` pointing at the offending step.

`validate-contract` schema-checks the contract, evaluates every assertion it
declares against the workbook's saved cached values, and prints
`{"invariants": [...], "all_passed": bool}`, where each entry in
`invariants` matches #34's `invariant_result` shape exactly (`{name,
passed, message?}`). Exit code is `0` if every declared invariant passed,
`2` if the contract was evaluated but one or more invariants failed, and `1`
only for a genuine caller error (a malformed contract, or a workbook that
can't be opened at all) -- printed the same `{"error": {code, message,
details}}` shape as `validate` and `dry-run`.

## Running the tests

```
pip install -r xlsx-win/v2/requirements.txt
python -m pytest xlsx-win/v2/tests/
```

(Run from the repository root, or from `xlsx-win/v2/` -- `tests/conftest.py`
puts `xlsx-win/v2/` on `sys.path` either way.)

## What "validation" means here (and does not)

Per RFC 0002 decision 6: validation in this module proves two things and
nothing more.

1. **Completion evidence** -- did the thing that was supposed to happen
   actually happen: does a required sheet/name/table exist, does a cached
   value look non-stale by an explicit rule, are there visible cached
   Excel errors anywhere in the workbook.
2. **Declared invariants** -- assertions a human (or a contract author)
   wrote down in advance: row-count minimums, sentinel cell values,
   freshness windows, an expected calculation mode.

It does **not** attempt to prove the workbook's *data* is semantically
correct -- there is no ground truth available to this tool for that. A
passing `validate-contract` run means "every assertion the contract author
wrote down in advance held," never "the numbers are right." Nobody should
read a passing result as proof of correctness; that boundary is stated here,
in `invariant_evaluator.py`'s module docstring, and in
`validation_contract.schema.json`'s own description, the same way RFC 0002
states it, precisely so it doesn't scope-creep later.

`invariant_evaluator.evaluate_contract()` reads the workbook with
`openpyxl(data_only=True)` -- the *cached* values as last saved, not live
formula recalculation. That is what lets it catch a stale cached workbook
that shows no visible formula errors: the acceptance criterion this module
exists to satisfy ("a stale cached workbook cannot pass solely because
formula cells contain no visible errors"). Every assertion declared in a
contract produces its own named `invariant_result` entry (e.g.
`"sentinel_cell:Summary!B2"`, `"min_row_count:Data"`,
`"freshness:Summary!A1"`), even when an earlier assertion in the same
contract already failed -- a caller sees the full picture in one pass.
`prohibit_visible_errors` reuses the exact list of Excel error values
`xlsx-win/scripts/check_formula_errors.py` already treats as significant
(imported by file path, not copied, so the two can't drift apart).

If a contract declares `expected_calculation_mode` and openpyxl cannot read
a calculation mode from the workbook's `calcPr`, the evaluator reports a
`passed: false` invariant with a `"not_checkable: ..."` message rather than
silently passing or crashing -- fail-closed, consistent with this module's
security-adjacent siblings (macro_policy, staging) rather than a silent
"assume it's fine."

## Macro policy, staging, and the audit manifest (#38), and what's out of scope

Three more small modules round out issue #38, each with one job:

- **`macro_policy.is_macro_approved(workbook_sha256, macro_name, allowlist)`**
  -- macros are disabled by default; a macro only runs if
  `(workbook_sha256, macro_name)` exactly matches an allowlist entry.
  Matching is exact: case-sensitive, no wildcards, no prefix/substring
  matching. This module owns the matching rule only -- it does not load,
  persist, or own the allowlist itself.
- **`staging.stage_copy(source_path)` / `staging.publish(staged_path,
  destination_path)`** -- per RFC 0002 decision 9, `stage_copy` always
  copies the source into a fresh `tempfile.mkdtemp()` directory, regardless
  of where the source lives (no OneDrive/SharePoint path-sniffing: staging
  locally is simpler and correct for every source). `publish` does **not**
  re-check invariants -- the caller must already have confirmed validation
  passed -- but refuses to publish a staged path that's missing or a
  zero-byte file, backs up any existing destination file to a timestamped
  path first, and swaps atomically (`os.replace`, with a
  copy-into-destination-directory-then-`os.replace` fallback when the
  staged file and destination are on different volumes).
- **`audit_manifest.build_audit_manifest(run_id, input_path, output_path,
  contract_path, invariant_results)`** -- links a run's input/output content
  hashes, the validation contract's path/hash if one was used, and the
  invariant results, redacting any invariant message that looks like a
  connection string, a credential embedded in a URL, or a bare access
  token before writing it into the manifest.

Explicitly **out of scope** for this single-user desktop deployment (RFC
0002 decisions 1-2, 6, 9):

- **Network egress policy** -- there is no network involved in this
  single-machine tool; egress control belongs to a hosted/multi-tenant
  deployment this repo does not build.
- **Credential handling** -- this control plane never stores or passes
  credentials. Excel's own connector credentials are handled by Excel,
  out of band, the same way they would be if a human opened the workbook
  directly.
- **Untrusted-workbook isolation via a separate worker pool** -- there is
  one machine and one worker here. "Untrusted" means "reject before Excel
  ever touches it" (macro_policy's job), not "quarantine in a pool." This
  issue does not build a queue, a worker pool, or a fencing-token protocol
  against concurrent workers -- enforcing "one job at a time" belongs to
  #36's supervisor, not to these five modules.

## Known interpretive decisions for #38

A few places in issue #38's spec left a modeling choice to this
implementation. Documented here so a caller isn't surprised:

- **Row counts.** For a plain sheet, `min_row_counts` counts every row with
  at least one non-empty cell, including any header row the sheet has --
  set the minimum accordingly (e.g. `header + expected data rows`). For an
  Excel Table (ListObject), the count excludes the table's own header
  row(s) (`Table.headerRowCount`), since a Table always declares a header
  by construction.
- **"Not checkable" calculation mode.** `invariant_result.passed` is a
  plain boolean (#34's schema has no third state), so when
  `expected_calculation_mode` is declared but openpyxl can't read a
  `calcMode` from the workbook, the evaluator reports `passed: false` with
  a message prefixed `"not_checkable: ..."` rather than inventing a
  three-valued result type. This is a deliberate fail-closed choice, not a
  claim that the calculation mode is actually wrong -- a caller that wants
  to distinguish "wrong" from "unknowable" should check for that message
  prefix.
- **Cross-volume publish test.** `tests/test_staging.py` exercises
  `staging.publish()`'s cross-volume fallback against a genuinely different
  local fixed volume (it probes for a second writable drive letter at test
  time) rather than mocking `os.replace()` to fake a volume boundary that
  isn't real. On a machine with only one fixed volume, that one test skips
  with an explanatory reason instead of asserting something that didn't
  happen; every other staging behavior (same-volume publish, backup,
  empty/missing-file refusal) is covered unconditionally.

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
