# Provenance

## Source

- Upstream repo or source document: `https://github.com/anthropics/skills`
- Upstream path: `skills/xlsx`
- Upstream commit/date: `57546260929473d4e0d1c1bb75297be2fdfa1949` / `2026-06-15`
- License reviewed: upstream `LICENSE.txt` is preserved in snapshots; redistribution policy requires separate review.

## Port Classification

- `port_depth`: `heavy-windows-com-adaptation`
- Verbatim copy: no
- Light adaptation: no
- Heavy adaptation: yes
- Original skill: no

## Design Upskill Contribution

Pinned provenance makes spreadsheet-design support reviewable. No-template visual work often depends on reliable chart data, calculated metrics, Power Query refresh, and formula-error checks. `xlsx-win` uses Excel COM because design polish is not useful if the workbook data or cached values are wrong.

## COM Boundary

Documentation, static validation, Python helper checks, and provenance checks can run in normal Codex execution. True Excel COM operations such as recalculation, Power Query refresh, workbook connection inspection, PivotTable state, and saved cached values may need desktop-user or elevated PowerShell, or a self-hosted Office runner.

## Intentional Divergences

| Upstream behavior | Local behavior | Reason | Test coverage |
| --- | --- | --- | --- |
| General spreadsheet skill behavior in `skills/xlsx` | Windows Excel COM-first workflow in `xlsx-win` | Excel desktop COM provides native recalculation, Power Query, cached values, PivotTable, and workbook connection fidelity | `xlsx-win/tests/` (pytest), `xlsx-win/supervisor/` C# unit + integration test projects, `xlsx-win/certification/run_corpus.py` / `smoke_test.ps1`; hosted syntax validation |
| Upstream implementation choices may use non-COM tooling | Local wrappers route COM work through shared preflight and desktop-user guidance | Codex sandbox sessions can be the wrong Windows logon context for Office COM | `.shared/office-com/scripts/office_com_preflight.ps1`; Office smoke workflow |
| Upstream guidance does not define a no-template chart-data reliability rubric | Local `references/workbook-quality-map.md` adds a workbook-quality behavior map for source data, formulas, refresh, Power Query, and chart-ready outputs | Codex needs explicit data reliability judgment before it builds no-template charts, dashboards, decks, or reports | `tools/test_office_com_contract.py`; hosted reference validation |
| v1's per-operation PowerShell scripts (`refresh_excel.ps1`, `power_query_excel.ps1`, `check_formula_errors.ps1`, `self_test_xlsx_win.ps1`, `invoke-xlsx-win.ps1`) | A versioned JSON job/result contract, a Python control plane, and a C# Windows supervisor that drives Excel COM against that contract | RFC-driven rewrite (`docs/rfcs/0001-xlsx-win-runtime-v2.md`, `docs/rfcs/0002-xlsx-win-v2-single-user-scope.md`; roadmap issue #33) for a bounded, auditable job contract instead of ad hoc script invocations. The old scripts were deleted outright, not kept alongside the new contract | `xlsx-win/tests/`, `xlsx-win/supervisor/` test projects, `xlsx-win/certification/`; see `xlsx-win/README.md` |

**Known regression accepted by this rewrite, not carried forward:** v1's `power_query_excel.ps1` could create, edit, or delete a Power Query M definition and change its load target. The v2 job contract can only refresh an *existing* connection -- authoring is not supported. Accepted deliberately rather than blocking the cutover on rebuilding that capability; tracked in issue #78.

## Last Alignment Review

- Reviewed date: 2026-06-16
- Reviewer: Codex Phase 3 Office runtime alignment pass
- Upstream commit compared: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Local commit reviewed: `74c04d0d16156e28f158d83aa38617e329cc1927`
- Result: workbook-quality behavior map added; non-COM workbook preparation and static contract checks are separated from Excel COM refresh, recalculation, Power Query, and cached-value validation that may require desktop-user or elevated PowerShell.
