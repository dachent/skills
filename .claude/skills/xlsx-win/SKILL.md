---
name: xlsx-win
description: windows excel desktop automation for .xlsx, .xlsm, .xls, .csv, and .tsv files in codex app or other local windows environments with microsoft 365 installed. use when chatgpt needs to open, inspect, edit, create, refresh, validate, or export spreadsheets on windows, especially workbooks with formulas, power query, pivottables, workbook connections, or cached values that require native excel com refresh. prefer this skill over pandas-only or libreoffice-based flows when excel desktop fidelity matters.
disable-model-invocation: true
---

# Xlsx Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/xlsx`
- Source branch: `main`

### Porting Notes

- This is a heavy Windows-specific adaptation of Anthropic's `xlsx` skill for Codex.
- The upstream skill centered on general spreadsheet editing guidance plus LibreOffice-backed recalculation.
- This port replaces that model with native Excel Desktop COM refresh and recalculation, explicit Power Query and `Workbook.Queries` handling, formula validation, self-test coverage, and Windows-specific macro and session policy guidance.
- It remains Windows-only because the intended behavior depends on Excel Desktop fidelity and COM refresh semantics rather than file-only spreadsheet editing.

Use this skill only for local execution on Windows machines with Microsoft 365 Excel desktop installed.

## Core Operating Rules

- Keep all workbook work local.
- Use native Excel for refresh and recalculation. Do not use LibreOffice.
- Treat workbook fidelity as important. Preserve existing sheets, formulas, named ranges, comments, formatting, widths, validations, workbook connections, and conventions unless the user asks for structural changes.
- Prefer Excel formulas over calculating values in Python and hardcoding them.
- Deliver workbooks with zero visible Excel error cells after refresh and validation.
- Match the workbook's existing template style and conventions exactly when editing an established file.
- Expect Excel COM refresh to require an interactive Windows desktop session. A Codex sandbox may block COM even when Excel is installed.
- Disable macros by default during automation. Only enable them when the user explicitly requests macro-dependent refresh or workbook automation.

## Workflow Decision Tree

1. **Need to confirm the environment works?**
   Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\self_test_xlsx_win.ps1
   ```

2. **Task is analysis, tabular cleanup, joins, or CSV/TSV normalization?**
   Use `pandas`. Export to `.xlsx` if the user wants a workbook deliverable.

3. **Task requires formulas, styles, comments, merged cells, or multi-sheet edits?**
   Use `openpyxl`. Prefer formulas over hardcoded values.

4. **Task requires Power Query M, `Workbook.Queries`, worksheet loads, or Data Model loads?**
   Use `xlsx-win\scripts\power_query_excel.ps1`. Read `xlsx-win\references\power-query-excel-com.md` for helper usage.

5. **Task requires workbook refresh, connection refresh, PivotTable update, or cached-value update?**
   Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\refresh_excel.ps1 -WorkbookPath output.xlsx
   ```

6. **Need to validate no formula errors remain?**
   Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\check_formula_errors.ps1 -WorkbookPath output.xlsx
   ```

## Quick Start

### Self-test
```powershell
powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\self_test_xlsx_win.ps1
```

### Refresh a workbook
```powershell
powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\refresh_excel.ps1 -WorkbookPath .\output.xlsx
```

### Validate formula errors
```powershell
powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\check_formula_errors.ps1 -WorkbookPath .\output.xlsx
```

### Upsert a Power Query query
```powershell
powershell -ExecutionPolicy Bypass -File xlsx-win\scripts\power_query_excel.ps1 `
  -WorkbookPath .\output.xlsx `
  -Action upsert-query `
  -QueryName MyQuery `
  -MFormulaPath .\my_query.m
```

## Standard Workflow

1. Inspect the source file and decide whether the task is primarily analysis, data cleanup, workbook editing, Power Query M work, conversion, or Excel-native refresh.
2. Choose `pandas`, `openpyxl`, `scripts/power_query_excel.ps1`, or direct Excel COM based on fidelity and Power Query needs.
3. Make the workbook edits.
4. Save the workbook.
5. If the task changes `Workbook.Queries` or query load targets, prefer `xlsx-win\scripts\power_query_excel.ps1` and pass `-MFormulaPath` for nontrivial M definitions.
6. If the output is `.xlsx` or `.xlsm` and formulas, refreshable objects, or cached values matter, run refresh:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\xlsx-win\scripts\refresh_excel.ps1 -WorkbookPath .\output.xlsx
   ```
7. Validate OOXML workbooks with:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\xlsx-win\scripts\check_formula_errors.ps1 -WorkbookPath .\output.xlsx
   ```
8. If the source is `.xls`, convert it to `.xlsx` before formula validation.
9. If the source is `.csv` or `.tsv`, skip formula validation unless you export it to an OOXML Excel workbook first.
10. If validation reports errors, fix the workbook and rerun refresh plus validation until clean.

## Power Query / M

Use native Excel Desktop COM for Power Query M work. Do not use file-only libraries to inspect, create, edit, refresh, or delete `Workbook.Queries`.

Treat each query as three separate artifacts:
- the M definition in `Workbook.Queries`
- the workbook connection
- the load target

Key rules:
- `Queries.Add(name, mFormula)` creates only the query definition. It does not create or update a worksheet load, a connection-only load, or a Data Model load.
- For existing queries, read and update the M definition in place. Preserve current query names, connections, and load settings unless the task explicitly changes them.
- If output must load to a worksheet, create or reuse the query's mashup OLE DB connection and load it explicitly to the requested sheet and range as a table.
- If output must load to the Data Model, create or add the model connection explicitly.
- When deleting a query, remove its sheet or model load and connection before deleting the query definition.
- After any M or load-setting change, run Excel refresh, wait for async queries to finish, save, and verify the expected table or model connection exists.

## Script Contracts

- `xlsx-win\scripts\refresh_excel.ps1`: refreshes, recalculates, saves, emits structured JSON. Exits `0` on success, `2` on failure.
- `xlsx-win\scripts\check_formula_errors.ps1`: validates visible Excel error cells. Exits `0` clean, `2` errors found, `1` scan failed.
- `xlsx-win\scripts\power_query_excel.ps1`: supports `upsert-query`, `load-worksheet`, `load-model`, `delete-query`. Emits structured JSON.
- `xlsx-win\scripts\self_test_xlsx_win.ps1`: smoke coverage for validator, refresh, path handling, macro policy, and Power Query actions.

## Formula Rule

Use Excel formulas instead of computing values in Python and writing hardcoded outputs whenever the workbook should remain dynamic.

- Use `=SUM(B2:B9)` instead of writing the precomputed total.
- Use `=(C4-C2)/C2` instead of writing a hardcoded growth rate.
- Put assumptions in cells and reference them from formulas instead of embedding constants directly into formulas.

## Refresh Workflow

Use `xlsx-win\scripts\refresh_excel.ps1` whenever any of these are true:
- the workbook contains formulas whose cached values may be stale
- the workbook contains workbook connections
- the workbook uses Power Query, PivotTables, or asynchronous queries
- the user explicitly wants native Excel refresh
- downstream users depend on values displayed in Excel rather than only stored formulas

## Validation Requirements

After refresh, inspect the JSON output from `check_formula_errors.ps1`:
- `status = success` means no Excel error cells were found.
- `status = errors_found` means the workbook must be fixed and revalidated.
- `status = error` means the scan itself failed.

Common Excel errors to eliminate: `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, `#NULL!`, `#NUM!`, `#N/A`, `#SPILL!`, `#CALC!`

## References

All scripts and references live under `xlsx-win\` relative to the repository root.

- `references\power-query-excel-com.md`: Power Query COM helper usage and patterns.
- `references\windows-excel-refresh.md`: refresh script execution details and troubleshooting.
- `references\spreadsheet-standards.md`: professional formatting and financial model conventions.
- `scripts\refresh_excel.ps1`: COM refresh, recalculate, save, and JSON status output.
- `scripts\check_formula_errors.ps1`: OOXML formula error validation via Python.
- `scripts\power_query_excel.ps1`: Power Query M upsert, load, model, and delete actions.
- `scripts\self_test_xlsx_win.ps1`: full local environment smoke test.
