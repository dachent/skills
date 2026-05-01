---
name: xlsx-win
description: Windows-only local Excel Desktop automation skill for `.xlsx`, `.xlsm`, `.xls`, `.csv`, and `.tsv` work that needs workbook fidelity, Excel COM refresh or recalculation, Power Query `Workbook.Queries` creation or update, worksheet table loads, connection-only queries, Data Model loads, or Excel environment self-test. Use when native Excel behavior matters on Windows, including workbook connections, cached values, PivotTables, Power Query, and macro-sensitive refresh when the user explicitly opts in. Do not use for cloud execution, non-Windows environments, Google Sheets API workflows, or machines without Microsoft 365 Excel desktop installed.
---

# XLSX Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/xlsx`
- Source branch: `main`

### Porting Notes

- This is a heavy Windows-specific adaptation of Anthropic's `xlsx` skill for Codex.
- The upstream skill centered on general spreadsheet editing guidance plus LibreOffice-backed recalculation.
- This port replaces that model with native Excel Desktop COM refresh and recalculation, explicit Power Query and `Workbook.Queries` handling, `power_query_excel.ps1`, formula validation, self-test coverage, and Windows-specific macro and session policy guidance.
- It remains Windows-only because the intended behavior depends on Excel Desktop fidelity and COM refresh semantics rather than file-only spreadsheet editing.

Use this skill only for Codex local execution on Windows machines with Microsoft 365 Excel desktop installed.

Before any Excel COM step, run the shared Office preflight from a regular PowerShell window opened as the signed-in desktop user:

```powershell
& "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps Excel
```

If preflight reports `can_use_com = false`, do not create `Excel.Application` from the Codex sandbox. Prepare the non-COM inputs in Codex and run the Excel COM step from that desktop-user PowerShell window through `scripts/invoke-xlsx-win.ps1` or a task-specific script.

## Core operating rules

- Keep all workbook work local.
- Use native Excel for refresh and recalculation. Do not use LibreOffice.
- Treat workbook fidelity as important. Preserve existing sheets, formulas, named ranges, comments, formatting, widths, validations, workbook connections, and workbook conventions unless the user asks for structural changes.
- Prefer Excel formulas over calculating values in Python and hardcoding them.
- Deliver workbooks with zero visible Excel error cells after refresh and validation.
- Match the workbook's existing template style and conventions exactly when editing an established file.
- Expect Excel COM refresh to require an interactive Windows desktop session. A Codex sandbox may block COM even when Excel is installed.
- Never call `New-Object -ComObject Excel.Application` directly from the Codex sandbox. Use the shared preflight first, then run COM work from the signed-in desktop user session through `scripts/invoke-xlsx-win.ps1` or a task-specific script.
- Disable macros by default during automation. Only enable them when the user explicitly requests macro-dependent refresh or workbook automation.

## Tool selection

Choose the lightest tool that preserves workbook fidelity.

- Use Excel Desktop COM for Power Query M work involving `Workbook.Queries`, query connections, worksheet loads, or Data Model loads.
- Prefer `scripts/power_query_excel.ps1` over ad hoc COM code for repeated or fragile Power Query create, load, model, and delete workflows.
- Use `pandas` for tabular analysis, joins, reshaping, cleanup, CSV and TSV normalization, and simple exports.
- Use `openpyxl` for formulas, formatting, comments, workbook-safe edits, widths, fills, defined names, and Excel-specific structure.
- Use `openpyxl` rather than pandas whenever formulas, comments, styles, merged cells, multiple sheets, or workbook conventions matter.
- After any change that introduces or depends on formulas, workbook connections, Power Query, PivotTables, or cached values in an OOXML workbook, run `scripts/refresh_excel.ps1` and then `scripts/check_formula_errors.ps1`.

## Power Query / M

Use native Excel Desktop COM for Power Query M work. Do not use file-only libraries to inspect, create, edit, refresh, or delete `Workbook.Queries`.

Treat each query as three separate artifacts:

- the M definition in `Workbook.Queries`
- the workbook connection
- the load target

Key rules:

- `Queries.Add(name, mFormula)` creates only the query definition. It does not create or update a worksheet load, a connection-only load, or a Data Model load.
- For existing queries, read and update the M definition in place. Preserve current query names, connections, and load settings unless the task explicitly changes them.
- If output must load to a worksheet, create or reuse the query's mashup OLE DB connection and load it explicitly to the requested sheet and range as a table, for example with `ListObjects.Add(...)` or `QueryTables.Add(...)`.
- If output must load to the Data Model, create or add the model connection explicitly, for example with `Connections.Add`, `Add2(..., CreateModelConnection:=True)`, or `Model.AddConnection`. If no load target is requested for a new query, default to connection-only.
- When deleting a query, remove its sheet or model load and connection before deleting the query definition.
- After any M or load-setting change, run Excel refresh, wait for async queries to finish, save, and verify that the expected table or model connection exists. For worksheet loads, also verify row counts look reasonable.

For supported helper usage, read `references/power-query-excel-com.md`.

## Script contracts

Use the bundled scripts as the stable contract surface for repetitive or fragile Excel work:

- `scripts/refresh_excel.ps1`
  - refreshes, recalculates, saves, and emits structured JSON
  - defaults to unique temp log and JSON artifact paths when not specified
  - disables macros by default; `-EnableMacros` is opt-in
  - exits `0` on success and `2` on operational failure
- `scripts/check_formula_errors.ps1`
  - validates visible Excel error cells in OOXML workbooks through `check_formula_errors.py`
  - depends on a usable Python interpreter with `openpyxl`
  - exits `0` on clean validation, `2` when findings are present, and `1` on operational error
- `scripts/power_query_excel.ps1`
  - supports `upsert-query`, `load-worksheet`, `load-model`, and `delete-query`
  - preserves existing query definitions and load settings unless the action explicitly changes them
  - prefer `-MFormulaPath` for nontrivial or multiline M to avoid shell-quoting issues
  - emits structured JSON for success and failure, including refresh artifact paths when refresh is required
- `scripts/self_test_xlsx_win.ps1`
  - creates temp workbooks and runs smoke coverage for validator, refresh, path handling, macro policy, and Power Query actions
  - use it when onboarding a new Windows machine, after changing these scripts, or when Excel COM behavior is in doubt

## Supported task types

Use this skill when the deliverable is a spreadsheet file and the task is any of the following:

- open, inspect, read, edit, or fix existing `.xlsx`, `.xlsm`, `.xls`, `.csv`, or `.tsv` files
- create a new spreadsheet from scratch or from other tabular data
- convert between spreadsheet and tabular formats
- clean messy exports into proper spreadsheets
- add columns, formulas, formatting, summaries, assumptions, charts, or model sections
- repair malformed rows, misplaced headers, junk footers, type issues, or broken references

Do not use this skill when the primary deliverable is a Word document, HTML report, standalone software package, database pipeline, or Google Sheets integration.

## Formula rule

Use Excel formulas instead of computing values in Python and writing hardcoded outputs whenever the workbook should remain dynamic.

Examples:

- Use `=SUM(B2:B9)` instead of writing the precomputed total.
- Use `=(C4-C2)/C2` instead of writing a hardcoded growth rate.
- Put assumptions in cells and reference them from formulas instead of embedding constants directly into formulas.

## Standard workflow

1. Inspect the source file and decide whether the task is primarily analysis, data cleanup, workbook editing, Power Query M work, conversion, or Excel-native refresh.
2. Run the shared Office preflight in the desktop-user PowerShell window before any Excel COM step.
3. Choose `pandas`, `openpyxl`, `scripts/power_query_excel.ps1`, or direct Excel COM based on fidelity and Power Query needs.
4. Make the workbook edits.
5. Save the workbook.
6. If the task changes `Workbook.Queries` or query load targets, prefer `scripts/power_query_excel.ps1` and pass `-MFormulaPath` for nontrivial M definitions.
7. If Codex is in the sandbox and preflight fails there, keep Codex on non-COM prep work and hand the COM step to the desktop-user shell through `invoke-xlsx-win.ps1`.
8. If the output is `.xlsx` or `.xlsm` and formulas, refreshable objects, or cached values matter, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\refresh_excel.ps1 -WorkbookPath .\output.xlsx
```

9. Validate OOXML workbooks with:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_formula_errors.ps1 -WorkbookPath .\output.xlsx
```

10. If the source is `.xls`, convert it to `.xlsx` before formula validation.
11. If the source is `.csv` or `.tsv`, skip formula validation unless you export it to an OOXML Excel workbook first.
12. If validation reports errors, fix the workbook and rerun refresh plus validation until clean.
13. If Excel COM or Power Query behavior is in doubt for the current machine, run `scripts/self_test_xlsx_win.ps1`.

## Refresh workflow

Use `scripts/refresh_excel.ps1` whenever any of these are true:

- the workbook contains formulas whose cached values may be stale
- the workbook contains workbook connections
- the workbook uses Power Query, PivotTables, or asynchronous queries
- the user explicitly wants native Excel refresh
- downstream users depend on values displayed in Excel rather than only stored formulas

The script opens Excel through COM, refreshes the workbook, waits for async work, performs a full rebuild calculation, waits for calculation to finish, saves, logs execution, writes a JSON status file, and exits nonzero on failure.

Refresh contract highlights:

- macros are disabled unless `-EnableMacros` is passed explicitly
- default log and JSON artifact paths are unique per run
- `status = success` means refresh and save completed
- `status = error` means the script failed operationally
- exit code `0` means success
- exit code `2` means operational failure

If Excel COM is blocked by the current session, treat that as an environment limitation, not as a workbook problem. The typical `0x80070520` failure means the shell is in the wrong Windows user or logon-session context. Rerun the refresh from the signed-in desktop user session through:

```powershell
& "$env:USERPROFILE\.codex\skills\xlsx-win\scripts\invoke-xlsx-win.ps1" -Action refresh -WorkbookPath .\model.xlsx
```

For direct Excel COM creation or targeted edits, use a task-specific PowerShell script only after the helper preflight succeeds in that same desktop-user shell.

See `references/windows-excel-refresh.md` for execution details and troubleshooting.

## Validation requirements

After refresh, inspect the JSON output from `scripts/check_formula_errors.ps1`.

- `status = success` means no Excel error cells were found.
- `status = errors_found` means the workbook must be fixed and revalidated.
- `status = error` means the scan itself failed.
- exit code `0` means clean validation
- exit code `2` means findings were detected
- exit code `1` means the validator itself failed
- if the validator fails with `python_not_found`, install or expose a Python interpreter with `openpyxl`

The validator supports `.xlsx`, `.xlsm`, `.xltx`, and `.xltm`. It returns structured JSON errors for unsupported formats such as `.xls`, `.csv`, and `.tsv`.

Common Excel errors to eliminate:

- `#REF!`
- `#DIV/0!`
- `#VALUE!`
- `#NAME?`
- `#NULL!`
- `#NUM!`
- `#N/A`
- `#SPILL!`
- `#CALC!`

## Professional output standards

Apply these standards unless the workbook already has established conventions that should be preserved.

- Use a consistent professional font.
- Avoid arbitrary reformatting of established templates.
- Keep formulas and layouts consistent across repeated periods and sections.
- Document important hardcodes, assumptions, and data sources.

For financial models and formatting conventions, see `references/spreadsheet-standards.md`.

## Verification checklist

Before returning a workbook that contains formulas or model logic, verify the following:

- test a few representative references before filling formulas broadly
- confirm row and column mapping is correct
- verify dependencies exist before writing formulas against them
- check nulls and denominator handling
- test edge cases including zero and negative values when relevant
- verify cross-sheet references use the intended sheet names and cells
- ensure there are no unintended circular references
- for Power Query changes, verify the intended worksheet or Data Model load target still exists after refresh
- for worksheet query loads, confirm the loaded table exists in the requested location and the row counts look reasonable
- rerun refresh and validation after structural edits or Power Query changes

## Library-specific guidance

### pandas

Use pandas for:
- reading messy tabular exports
- fixing malformed headers or repeated header rows
- trimming junk footer rows
- type cleanup and joins
- bulk transformations before export to Excel

### openpyxl

Use openpyxl for:
- preserving workbook structure
- inserting formulas rather than hardcoded outputs
- styling, fills, comments, widths, and sheet-level edits
- modifying existing multi-sheet workbooks safely

Important openpyxl warnings:
- workbook indices are 1-based
- `data_only=True` reads cached values, not formulas
- if a workbook opened with `data_only=True` is saved, formulas can be lost
- openpyxl preserves formulas as strings but does not calculate them; use the PowerShell refresh script to update cached values

## Code generation style

When generating code for Excel operations:

- keep code minimal and direct
- avoid unnecessary comments and print statements
- prefer clear but concise variable names
- do not compute values in Python when the correct deliverable is an Excel formula
