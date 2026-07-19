---
name: xlsx-win
description: native microsoft excel automation for windows .xlsx/.xlsm/.xls/.csv/.tsv workflows. use when chatgpt, codex, or claude code is running on windows with microsoft 365 excel installed and needs to refresh, recalculate, validate, or route a workbook through excel com automation. trigger for workbook connections, cached values, pivottables, calculation correctness, refreshing an existing power query connection, data model-aware routing, chart-ready data, no-template spreadsheet deliverables, or excel environment self-test. does not support authoring or editing power query m code, or macro execution -- see "known gaps" below. do not use for cloud execution, non-windows environments, google sheets api workflows, or machines without excel desktop installed.
---

# XLSX Win

## Notes

### Provenance

- Originally ported from `https://github.com/anthropics/skills` (`skills/xlsx`) as a heavy Windows/COM adaptation -- see `PROVENANCE.md`.
- Rewritten as "v2": a versioned JSON job/result contract, a Python control plane (schema validation, deterministic file-backend routing, workbook validation contracts, macro policy, staging), and a C# Windows supervisor that drives Excel COM against that contract. Durable design record: `docs/rfcs/0001-xlsx-win-runtime-v2.md` and `docs/rfcs/0002-xlsx-win-v2-single-user-scope.md`. Roadmap and full history: issue #33 and its linked issues.
- This replaced the original PowerShell-script surface (`refresh_excel.ps1`, `power_query_excel.ps1`, `check_formula_errors.ps1`, `self_test_xlsx_win.ps1`, `invoke-xlsx-win.ps1`) entirely -- those scripts no longer exist in this repo. See "Known gaps vs the retired v1 scripts" below for what that cutover did and did not carry forward.

## Design Upskill Contribution

Use `xlsx-win` to teach the agent that no-template design depends on reliable workbook data before it depends on visual polish. The skill contributes:

- calculation correctness through native Excel refresh, recalculation, and validation contracts,
- workbook connection discipline (per-connection refresh, never a bare `RefreshAll`) so loaded data can be trusted,
- chart-ready data guidance for downstream decks, reports, dashboards, and workbook visuals,
- a clear non-COM versus COM split so the agent can prepare workbook structure safely and hand true refresh/recalculation to Excel when required.

Read `references/workbook-quality-map.md` when a task asks for a polished workbook, dashboard source table, analysis pack, model, chart-ready dataset, or spreadsheet that will feed a no-template visual artifact.

Use this skill only for local execution on Windows machines with Microsoft 365 Excel desktop installed.

Before any Excel COM step, run the shared Office preflight from the session that will actually invoke `control_plane/cli.py run`:

```powershell
& "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps Excel
```

That path assumes a Codex-style install. If this skill is loaded through a Claude Code plugin instead, resolve the same script from the plugin cache first:

```powershell
$preflight = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache" -Recurse -Filter "office_com_preflight.ps1" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $preflight) { $preflight = "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" }
& $preflight -Apps Excel
```

If preflight reports `can_use_com = false`, this session cannot run Excel-touching steps. Unlike v1, there is currently no dedicated sandboxed-agent-to-desktop-user handoff script for v2 (`invoke-xlsx-win.ps1` had no replacement built during the cutover -- see issue #79): hand the actual `cli.py run` invocation to an interactive desktop-user PowerShell session yourself.

For a new machine, after an Office update, or whenever Excel COM behavior is in doubt, run the environment self-test:

```powershell
powershell -ExecutionPolicy Bypass -File certification/smoke_test.ps1
```

This builds/uses the supervisor and runs the full certification corpus against real Excel: router decisions, a genuine Power-Query-connection refresh, validation contracts, and macro-policy rejection. It's the same entrypoint CI uses (`.github/workflows/office-smoke.yml`).

## Core operating rules

- Keep all workbook work local.
- Use native Excel for refresh and recalculation. Never use LibreOffice or a file-only library to refresh a workbook connection.
- Treat workbook fidelity as important. Preserve existing sheets, formulas, named ranges, comments, formatting, widths, validations, workbook connections, and workbook conventions unless the user asks for structural changes.
- Prefer Excel formulas over hardcoded values computed in Python -- see "Formula rule" below.
- Deliver workbooks with zero visible Excel error cells after refresh and validation.
- Match the workbook's existing template style and conventions exactly when editing an established file.
- Macros are disabled by default and cannot currently be executed through this skill at all -- see "Known gaps" below.
- Expect Excel COM automation to require an interactive Windows desktop session. Whether a sandboxed agent session can launch it directly is currently untested -- see issue #79. If a job fails in a way that looks like Excel COM could not be created (not a workbook problem), that is the likely cause; run the shared preflight, then run the job from an interactive desktop session.
- For no-template spreadsheet deliverables, use `references/workbook-quality-map.md` to separate raw data, cleaned tables, assumptions, calculations, and outputs before adding visual polish.

## Tool selection

Choose the lightest tool that preserves workbook fidelity. Route the decision deterministically instead of guessing:

```
python control_plane/cli.py route <workbook.xlsx> <create_new|edit_existing|convert_format>
```

This inspects the workbook's real OOXML package (macros, signature, external links, Data Model, pivots, slicers, embedded objects, workbook connections) and returns one of:

- `xlsxwriter` -- new formatted workbook, no existing file to preserve.
- `openpyxl` -- editing an existing plain workbook with none of the above risk features.
- `excel_required` -- any workbook with a risk feature above. Never edit these with a file-only library; a successful-looking edit is not evidence the workbook's structure survived intact.
- `convert_required` -- legacy binary `.xls`; convert to `.xlsx` before any Python-side edit (no automated conversion step exists yet -- do this manually, e.g. by opening and re-saving in Excel).
- `not_applicable` -- `.csv`/`.tsv`; this router has no opinion on plain delimited text.

Use `pandas` for tabular analysis, joins, reshaping, cleanup, CSV/TSV normalization, and simple exports. Use `openpyxl` for formulas, formatting, comments, workbook-safe edits, widths, fills, defined names, and Excel-specific structure whenever the router says `openpyxl`. For anything the router says `excel_required`, use the job contract below -- never fall back to `openpyxl` just because it happens to open the file without erroring.

## Power Query / connections

**Refreshing an existing Power Query connection or workbook connection is fully supported** through the job contract's `refresh` step (see below) -- it refreshes each connection individually (not a bare `RefreshAll`), with per-connection error handling.

**Creating, editing, or deleting a Power Query M definition, or changing its load target (worksheet vs. Data Model), is not currently supported by this skill.** The v1 script that did this (`power_query_excel.ps1`) was retired in the v2 cutover with no replacement built yet -- see issue #78. If a task requires authoring or modifying Power Query M code, tell the user this isn't currently automatable through this skill and the query must be created/edited by hand in Excel first; this skill can then refresh it once it exists.

## The job contract

The stable, versioned interface for anything that needs real Excel: a JSON job manifest describing an ordered list of steps, executed by a C# supervisor that owns the Excel process, enforces per-phase timeouts, and force-terminates cleanly (via a Windows Job Object, never a by-name process kill) if a phase runs over. See `README.md` for the full schema and `supervisor/README.md` for the supervisor's internals; this section is the short version.

A job is `{schema_version, idempotency_key, steps, timeouts}`. Each step is one of:

- `open` -- `{workbook_path, read_only?, update_links?}`
- `refresh` -- `{connections: "all" | [names]}` -- refreshes each named connection individually, never a bare `RefreshAll`
- `recalc` -- `{mode: "full_rebuild" | "normal"}`
- `save_as` -- `{output_path, overwrite?}`
- `run_approved_macro` -- **not implemented.** Any job containing this step fails with `MACRO_EXECUTION_DEFERRED` by design, not silently. See "Known gaps" below and issue #73.

A result is `{schema_version, run_id, idempotency_key, final_state, steps, invariants, ok}`. **Always check the top-level `ok` boolean, never infer success from `final_state` or individual step statuses yourself** -- `ok` is computed by the contract layer and is `true` if and only if every step succeeded and every declared invariant (see "Validation contracts" below) passed.

CLI subcommands (`python control_plane/cli.py <subcommand>`):

- `validate <manifest.json>` -- schema-check only, no Excel needed.
- `dry-run <manifest.json>` -- schema-check plus prints the state sequence the job would traverse, no Excel needed.
- `route <workbook> <intent>` -- see "Tool selection" above, no Excel needed.
- `validate-contract <workbook> <contract.json>` -- see "Validation contracts" below, reads the workbook with openpyxl, no Excel COM.
- `run <manifest.json>` -- the only subcommand that actually launches Excel. Validates first (fails closed before touching anything if the manifest is invalid), stages the `open` step's input to a local temp copy before ever opening it (the manifest's real input path is never touched directly), invokes the supervisor, and -- only if the result reports `ok: true` -- publishes any `save_as` output to its real target. A failed job leaves every original path completely untouched.

Before `run` can do anything, the C# supervisor must be built: `dotnet build supervisor/XlsxWinSupervisor.slnx`. If it isn't built yet, `run` fails with a clear message pointing at that command, not a confusing crash.

## Validation contracts

A sidecar JSON contract per workbook can declare: required sheets/defined names/tables, minimum row counts, exact sentinel cell values, a maximum data-freshness window, whether visible Excel error values are prohibited, and an expected calculation mode. `validate-contract` evaluates every declared assertion against the workbook's saved *cached* values (not live formulas) and reports each one's pass/fail individually.

**What this proves, and does not prove:** a passing validation contract means every assertion the contract author wrote down in advance held -- completion evidence and declared invariants, nothing more. It is never proof that the underlying numbers are semantically correct; there is no ground truth available to this tool for that. Never represent a passing contract as "the data is correct" -- only as "what was checked, checked out."

Macro policy (`macro_policy.py`) is a related, separate piece: an exact-match allowlist by workbook hash + macro entrypoint, disabled by default. It currently has nothing to gate, since macro execution itself is unimplemented (see below).

## Standard workflow

1. Inspect the source file and decide whether the task is primarily analysis, data cleanup, workbook editing, or Excel-native refresh/recalculation.
2. If the source is `.xls`, convert it to `.xlsx` manually first (no automated step exists).
3. If the source is `.csv` or `.tsv`, skip the job contract entirely unless you first export it to an OOXML workbook.
4. Run `route` to decide the backend deterministically -- don't guess from "this workbook looks simple."
5. If the router says `xlsxwriter` or `openpyxl`, do the edit with that library directly.
6. If the router says `excel_required`, build a job manifest with the steps you need (typically `open` → `refresh` → `recalc` → `save_as`), `validate` it, optionally `dry-run` it, then `run` it.
7. Check the result's top-level `ok` field. If `false`, inspect `steps` for which one failed and why before doing anything else.
8. If the workbook has correctness properties worth asserting (expected row counts, sentinel values, freshness), write a validation contract and run `validate-contract` against the output.

## Known gaps vs the retired v1 scripts

The v1 PowerShell-script surface this replaced had capabilities the v2 rewrite does not yet have. These are deliberate, tracked gaps, not oversights -- do not attempt to work around them with `openpyxl` or a hand-rolled COM script; tell the user what isn't currently supported instead.

- **Power Query M authoring** (create, edit, or delete a query; change its load target) -- not supported. Issue #78. Refreshing an *existing* connection is fully supported.
- **Macro execution** -- not supported. `run_approved_macro` always fails with `MACRO_EXECUTION_DEFERRED`. Issue #73 (deliberately deferred).
- **Sandboxed-agent COM access** -- untested. Every real Excel job in this rewrite's own development was run from an already-interactive desktop session; whether the supervisor works when launched from inside a sandboxed agent process (the way the old scripts needed an explicit desktop-user handoff) is unverified. Issue #79.
- **Heartbeat liveness signal** during a long refresh exists but has never been observed firing for a genuine Power Query connection on the machines this was built and tested on (`Refresh()` blocks synchronously for the connection's whole duration for that connection type) -- treat it as a nice-to-have diagnostic, not something to rely on for detecting a stuck job. The supervisor's own phase-deadline timeout is the real bound.

## Professional output standards

Apply these standards unless the workbook already has established conventions that should be preserved.

- Use a consistent professional font.
- Avoid arbitrary reformatting of established templates.
- Keep formulas and layouts consistent across repeated periods and sections.
- Document important hardcodes, assumptions, and data sources.

For financial models and formatting conventions, see `references/spreadsheet-standards.md`.
For no-template workbook structure, chart-ready data, and calculation evidence, see `references/workbook-quality-map.md`.

## Formula rule

Use Excel formulas instead of computing values in Python and writing hardcoded outputs whenever the workbook should remain dynamic.

- Use `=SUM(B2:B9)` instead of writing the precomputed total.
- Use `=(C4-C2)/C2` instead of writing a hardcoded growth rate.
- Put assumptions in cells and reference them from formulas instead of embedding constants directly into formulas.

## Verification checklist

Before returning a workbook that contains formulas or model logic, verify the following:

- test a few representative references before filling formulas broadly
- confirm row and column mapping is correct
- verify dependencies exist before writing formulas against them
- check nulls and denominator handling
- test edge cases including zero and negative values when relevant
- verify cross-sheet references use the intended sheet names and cells
- ensure there are no unintended circular references
- for a job that included a `refresh` step, confirm the result's `ok` field is `true` and check each connection's per-step outcome, not just the overall `final_state`
- rerun `run` and `validate-contract` after structural edits

## Library-specific guidance

### pandas

Use pandas for reading messy tabular exports, fixing malformed/repeated header rows, trimming junk footer rows, type cleanup and joins, and bulk transformations before export to Excel.

### openpyxl

Use openpyxl for preserving workbook structure, inserting formulas rather than hardcoded outputs, styling/fills/comments/widths/sheet-level edits, and modifying existing multi-sheet workbooks the router has confirmed are safe to touch this way.

Important openpyxl warnings:
- workbook indices are 1-based
- `data_only=True` reads cached values, not formulas
- if a workbook opened with `data_only=True` is saved, formulas can be lost
- openpyxl preserves formulas as strings but does not calculate them; use a `refresh`/`recalc` job to update cached values

## Code generation style

When generating code for Excel operations:

- keep code minimal and direct
- avoid unnecessary comments and print statements
- prefer clear but concise variable names
