# xlsx-win v2 control plane -- contract, validation, policy, and the CLI that runs a job for real

This directory implements issue #34 (the LLM-facing job/result contract),
issue #35 (the deterministic file-backend router), issue #38 (workbook
validation contracts, macro policy, staging, and the audit manifest), issue
#71 (`cli.py run`, wiring the CLI to the real C# supervisor), and issue #72
(wiring #38's staging/publish primitives into `run`'s own call path, plus
IMessageFilter COM-retry handling and a refresh heartbeat on the C# side --
see `supervisor/README.md`) for the xlsx-win v2 runtime, scoped to a single
desktop per
[RFC 0002](../../docs/rfcs/0002-xlsx-win-v2-single-user-scope.md) (which
amends [RFC 0001](../../docs/rfcs/0001-xlsx-win-runtime-v2.md)).

## Scope

**Everything in this directory except one subcommand is contract,
validation, and policy only -- no Excel, no COM.** The one exception:
`cli.py run` resolves and invokes the built `XlsxWinSupervisor.exe` (#36) as
a subprocess, which is what actually drives Excel -- one process boundary
away, never inside this Python process itself. See "Using the CLI" and
"Running a job for real (`run`, issues #71/#72)" below.

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
- A CLI that validates and dry-runs manifests, evaluates workbook validation
  contracts, and (via `run`) actually invokes the built supervisor
  (`control_plane/cli.py`).
- Executable-resolution and subprocess-invocation for the built
  `XlsxWinSupervisor.exe`/`XlsxWinWorker.exe`, shared between `cli.py run`
  and the certification scripts
  (`control_plane/supervisor_runner.py` -- issue #71).

No module in this directory imports `pywin32` or calls Excel COM directly.
`invariant_evaluator.py` is the one module that reads a workbook file (with
openpyxl, read-only, cached values); `supervisor_runner.py` is the one
module that can cause Excel to run, indirectly, by launching the built
`XlsxWinSupervisor.exe` as a subprocess -- the actual Excel COM automation
happens entirely inside that separate executable (issue **#36**), never in
this Python process. Everything else here is pure Python over JSON
documents and the filesystem.

## Layout

```
xlsx-win/
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
    workbook_inventory.py     # inspect_workbook(path) -- reads the OOXML package directly
    file_router.py             # choose_backend(intent, inventory) -- deterministic routing
    supervisor_runner.py        # find_built_exe(...) / run_supervisor(...) -- #71, no Excel gate
    cli.py                    # `validate`, `dry-run`, `route`, `validate-contract`, `run` subcommands
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
pip install -r xlsx-win/requirements.txt
```

`jsonschema` backs the job/result contract (#34) -- there is no JSON-Schema
validator in the Python standard library, and RFC 0001 requires the contract
to be JSON-Schema-backed. `openpyxl` and `xlsxwriter` are the two real
backends the router (#35) chooses between, and `openpyxl` is also what
`invariant_evaluator.py` (#38) uses to read a saved workbook's cached
values -- never to drive Excel. Neither is imported by
`workbook_inventory.py` itself, which inspects OOXML packages directly
instead of opening them.

## Using the CLI

Four of the five subcommands work with no Excel installed. `route` and
`validate-contract` do read the workbook file itself (`route` via a direct
OOXML package inspection, `validate-contract` with openpyxl), but neither
launches Excel or touches COM. `run` is the exception -- see the next
section.

```
python xlsx-win/control_plane/cli.py validate           <manifest.json>
python xlsx-win/control_plane/cli.py dry-run            <manifest.json>
python xlsx-win/control_plane/cli.py route              <workbook.xlsx> <create_new|edit_existing|convert_format>
python xlsx-win/control_plane/cli.py validate-contract  <workbook.xlsx> <contract.json>
python xlsx-win/control_plane/cli.py run                <manifest.json> [--events PATH] [--result PATH] [--hard-timeout-seconds N]
```

`validate` schema-checks the manifest and prints `{"valid": true}` or
`{"valid": false, "error": {code, message, details}}` (exit code 1 on
failure). `dry-run` does the same schema check, then prints the state
sequence the job would traverse -- including, on a schema failure inside one
of the steps, a `details.json_path` pointing at the offending step. `route`
inspects the workbook's OOXML package and prints the resulting
`RouterDecision` (`backend`, `reason`, `explain`) as JSON.

`validate-contract` schema-checks the contract, evaluates every assertion it
declares against the workbook's saved cached values, and prints
`{"invariants": [...], "all_passed": bool}`, where each entry in
`invariants` matches #34's `invariant_result` shape exactly (`{name,
passed, message?}`). Exit code is `0` if every declared invariant passed,
`2` if the contract was evaluated but one or more invariants failed, and `1`
only for a genuine caller error (a malformed contract, or a workbook that
can't be opened at all) -- printed the same `{"error": {code, message,
details}}` shape as `validate` and `dry-run`.

## Running a job for real (`run`, issues #71/#72)

`run` is the one subcommand that ends up driving real Excel -- indirectly,
by invoking the built `XlsxWinSupervisor.exe` (#36) as a subprocess. It is
the thing that lets a single CLI invocation take a job manifest all the way
from schema validation to a real Excel-driven result:

```
python xlsx-win/control_plane/cli.py run manifest.json
```

What it does, in order:

1. Loads and schema-validates the manifest exactly like `validate` does
   (`schemas.validate_job`). **If this fails, it fails closed and returns
   before ever resolving, staging, or touching the supervisor** -- prints
   the same `{"valid": false, "error": {code, message, details}}` shape,
   exit code 1.
2. **Pre-touch staging (issue #72, RFC 0002 decision 9).** If the manifest
   has an `open` step, its `workbook_path` is staged into a fresh local
   temp copy via the already-existing, already-tested #38
   `staging.stage_copy` -- built once and reused here, not reimplemented --
   and an *in-memory* copy of the parsed job dict has that step's
   `workbook_path` rewritten to point at the staged copy. **The caller's
   on-disk manifest file itself is never mutated**, and the manifest's real
   input path is never opened directly -- every step from here on runs
   against the staged copy. Any `save_as` step's `output_path` is likewise
   rewritten to a path inside that same staging directory, so the real save
   target is never written to directly either. A manifest with no `open`
   step degrades gracefully: nothing is staged, and `run` invokes the
   supervisor against the caller's original manifest file exactly as issue
   #71 did before staging existed.
3. Resolves the built `XlsxWinSupervisor.exe`/`XlsxWinWorker.exe` and
   invokes the supervisor as a subprocess
   (`control_plane/supervisor_runner.py`) against the *staged* manifest (or
   the original, if nothing was staged), passing it an events path and a
   result path (see "Job/result JSON file-path contract" in
   `supervisor/README.md` -- these still default next to the *original*
   manifest path, not the staged one, so they stay discoverable). If the
   executables can't be found, or the supervisor subprocess doesn't exit
   within a generous wall-clock safety-net timeout, `run` prints
   `{"valid": false, "error": {"code": "SUPERVISOR_INVOCATION_FAILED",
   ...}}` and returns exit code 1 -- still without ever having started
   Excel.
4. Reads back `result.json`. **Only if it reports `ok: true` and the job had
   one or more `save_as` steps**, calls `staging.publish` for each one,
   atomically swapping that step's staged output into its real, original
   `output_path` (backing up any existing file there first -- see
   `staging.py`). If the job failed (`ok: false`, or the result document
   couldn't even be read), **nothing is published and every original
   `save_as.output_path` is left completely untouched** -- this is RFC 0002
   decision 9's whole point, not a best-effort partial write.
5. Prints the result document and **exits with the supervisor's own exit
   code, unmodified** -- `run` never reinterprets or wraps it (see
   supervisor/README.md's own exit-code contract: `0` success, `1` forced
   timeout kill, `2` argument/manifest error). A caller must read the
   printed result document's `final_state`/`ok` fields to learn the *job's*
   outcome; the process exit code alone only tells you whether the
   supervisor itself ran cleanly. (Exception: if step 4's `staging.publish`
   itself fails -- a rare last-ditch sanity-check failure, e.g. a zero-byte
   staged output -- `run` prints that error instead and returns exit code 1
   regardless of the supervisor's own exit code.)

`run` does **not** call `file_router.choose_backend` and does not dispatch
to a non-Excel backend -- a job manifest's steps (`open`/`refresh`/
`recalc`/`save_as`/`run_approved_macro`) are already inherently Excel-COM
operations by construction. Deciding whether Excel is even needed for a
given piece of work is a separate, earlier decision a caller makes via
`route`, before ever building a job manifest -- not something `run`
second-guesses.

### Choosing events/result paths

`--events`/`--result` default to sibling files next to the manifest:
`<manifest-stem>.events.jsonl` and `<manifest-stem>.result.json` in the same
directory as the manifest (e.g. `job.json` -> `job.events.jsonl` /
`job.result.json`). Pass `--events`/`--result` explicitly to point
elsewhere (a temp directory, a per-run subdirectory, etc.) -- useful for
running the same manifest repeatedly without each run's events/result
overwriting the last one's in place.

### Locating the built executables (`control_plane/supervisor_runner.py`)

`supervisor_runner.find_built_exe(project_name)` resolves each executable in
this order:

1. **A deployment-override environment variable** --
   `XLSXWIN_SUPERVISOR_EXE_PATH` for `XlsxWinSupervisor.exe`,
   `XLSXWIN_WORKER_EXE_PATH` for `XlsxWinWorker.exe` -- if set, must point at
   an existing file (a missing target raises immediately, never silently
   falls back). This is the intended real-deployment story: `dotnet publish`
   the two executables somewhere stable outside this dev checkout, then set
   both env vars once in the environment `cli.py run` runs in.
   `XLSXWIN_WORKER_EXE_PATH` is also the exact variable the supervisor
   itself reads to learn which worker binary to launch (see
   `supervisor/README.md`, "Locating the worker executable") -- the same
   value serves both purposes, so there's one source of truth, not two.
2. **The dev-tree convention** -- the newest `<project_name>.exe` found
   under `xlsx-win/supervisor/<project_name>/bin/**`, i.e. whatever a
   plain `dotnet build` (see `supervisor/README.md`) most recently produced
   in this checkout. This is what a developer working directly in this repo
   gets with no configuration.

**If neither resolves**, `find_built_exe` raises `FileNotFoundError` with a
message that both names the path it searched and points at the fix: build
the solution first with
`dotnet build xlsx-win/supervisor/XlsxWinSupervisor.slnx`. `cli.py run`
surfaces that message inside its normal `{"error": {...}}` JSON shape
(`SUPERVISOR_INVOCATION_FAILED`) rather than letting a raw Python traceback
reach the caller.

`certification/excel_safety.py` now imports `find_built_exe` and the core of
`run_supervisor` from `supervisor_runner.py` instead of maintaining its own
copy -- it layers its Excel-launch safety gate (opt-in env var, preflight,
postflight) on top, which `cli.py run` deliberately does not apply itself
(see that module's own docstring for why: `run` is an explicit,
one-shot, interactively-invoked command, the same trust model as a human
opening Excel by hand -- not an unattended test harness). A caller that
wants the same guardrails around `run` can layer
`excel_safety.preflight_or_raise()` / `excel_safety.assert_no_excel_survives()`
around it exactly as `run_corpus.py` does.

## Running the tests

```
pip install -r xlsx-win/requirements.txt
python -m pytest xlsx-win/tests/
```

(Run from the repository root, or from `xlsx-win/` -- `tests/conftest.py`
puts `xlsx-win/` on `sys.path` either way.)

`tests/test_run_subcommand.py` covers `run`'s manifest-validation and
executable-resolution failure paths unconditionally (no Excel needed), plus
one real end-to-end invocation against the actual built supervisor, gated
behind `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1` and
`certification/excel_safety.py`'s existing preflight/postflight (skips
cleanly, not a failure, when the env var isn't set or Excel is already
running).

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
`prohibit_visible_errors` checks against the same list of significant Excel
error values (`#VALUE!`, `#DIV/0!`, `#REF!`, `#NAME?`, `#NULL!`, `#NUM!`,
`#N/A`, `#SPILL!`, `#CALC!`) the retired v1 `check_formula_errors.py` script
used -- inlined directly in `invariant_evaluator.py` now that the script it
used to be imported from by file path no longer exists.

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
  staged file and destination are on different volumes). Issue #72 is the
  first real caller of these two functions from the actual job-execution
  path: `cli.py run` calls `stage_copy` on the manifest's `open` step before
  ever invoking the supervisor, and `publish` on any `save_as` step's
  staged output once (and only once) the supervisor reports `ok: true` --
  see "Running a job for real" above. Their own signatures/behavior are
  unchanged by #72; only the call site is new.
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
