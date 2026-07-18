# Excel no-template workbook quality map

Use this map when `xlsx-win` has to create or reshape a workbook that will feed analysis, charts, dashboards, or decision documents without an existing template.

## Purpose

Spreadsheet design quality starts with trustworthy data behavior. A polished chart, deck, or report is fragile if formulas are stale, Power Query loads are broken, or workbook structure is hard to audit. Codex should design workbooks so the data layer, calculation layer, and presentation layer can each be checked.

## Quality dimensions

| Dimension | What to do | Why it matters | Verification |
| --- | --- | --- | --- |
| Source data | Keep raw imports, cleaned tables, assumptions, calculations, and outputs on clearly named sheets or tables. | Separation makes the workbook inspectable and prevents chart data from depending on hidden manual edits. | Inspect sheet names, table names, and row counts before chart or report export. |
| Formula design | Use formulas for dynamic values, reference assumption cells, and keep formulas consistent across repeated rows or periods. | No-template workbooks must remain reusable after the first generated output. | Refresh/recalculate in Excel, then run formula-error validation. |
| Calculation state | Rebuild calculation when formulas, external links, PivotTables, Power Query, or cached values matter. | Cached values can be stale even when formulas look correct in OOXML. | Run a job manifest with `refresh`/`recalc` steps through `control_plane/cli.py run` from an Excel COM-capable session. |
| Power Query | Treat the M definition, workbook connection, and load target as separate objects. | Query definitions alone do not guarantee visible tables or Data Model loads. | After refresh, verify worksheet table or Data Model connection existence and row counts. |
| Chart-ready outputs | Create tidy output tables with explicit labels, units, time periods, and denominators. | Downstream visual design needs reliable encodings and readable labels. | Review output tables before charting and confirm there are no Excel error values. |
| Formatting | Match existing workbook conventions or apply a restrained, consistent grid, number format, and header system. | Formatting should improve scanning without hiding calculation logic. | Inspect representative sheets and confirm formulas, comments, widths, and validations were preserved. |
| Macro policy | Disable macros by default and enable them only with explicit user consent. | Workbook automation should not execute unknown code accidentally. | Check refresh JSON macro policy and document any opt-in macro use. |

## Chart-ready data rules

- Prefer one table per intended chart grain.
- Include human-readable labels, machine-sortable dates or periods, numeric measures, and units.
- Keep denominators or sample sizes next to rates and percentages.
- Do not feed charts from merged-cell presentation ranges when a clean table can exist nearby.
- Preserve formula-driven outputs unless the user explicitly asks for static values.
- Validate that visible errors such as `#REF!`, `#DIV/0!`, and `#NAME?` are gone before using the workbook as a visual source.

## Non-COM vs COM split

Normal Codex execution can inspect OOXML structure, edit formulas, build cleaned tables, write Power Query M text files, create static workbooks, and run `control_plane/cli.py validate-contract` (openpyxl only, no Excel COM) against supported OOXML files.

True Excel COM is required to prove or perform:

- native refresh and full calculation rebuild,
- async Power Query completion,
- workbook connection and Data Model behavior,
- PivotTable refresh state,
- saved cached values as Excel would display them,
- macro-dependent refresh when the user explicitly opts in.

If COM preflight fails in Codex, continue with non-COM workbook preparation and move only the refresh/recalculation/Power Query validation step to a signed-in desktop-user PowerShell session or the self-hosted Office runner.

## Contribution to design upskill

This reference teaches Codex that spreadsheet design is the reliability layer beneath no-template visuals. It gives the agent a repeatable way to decide whether data is chart-ready and whether visual polish is backed by Excel-native calculation evidence.
