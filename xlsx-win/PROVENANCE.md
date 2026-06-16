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
| General spreadsheet skill behavior in `skills/xlsx` | Windows Excel COM-first workflow in `xlsx-win` | Excel desktop COM provides native recalculation, Power Query, cached values, PivotTable, and workbook connection fidelity | `xlsx-win/scripts/self_test_xlsx_win.ps1`, `xlsx-win/scripts/check_formula_errors.ps1`; hosted syntax validation |
| Upstream implementation choices may use non-COM tooling | Local wrappers route COM work through shared preflight and desktop-user guidance | Codex sandbox sessions can be the wrong Windows logon context for Office COM | `.shared/office-com/scripts/office_com_preflight.ps1`; Office smoke workflow |
| Upstream guidance does not define a no-template chart-data reliability rubric | Local `references/workbook-quality-map.md` adds a workbook-quality behavior map for source data, formulas, refresh, Power Query, and chart-ready outputs | Codex needs explicit data reliability judgment before it builds no-template charts, dashboards, decks, or reports | `tools/test_office_com_contract.py`; hosted reference validation |

## Last Alignment Review

- Reviewed date: 2026-06-16
- Reviewer: Codex Phase 3 Office runtime alignment pass
- Upstream commit compared: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Local commit reviewed: `74c04d0d16156e28f158d83aa38617e329cc1927`
- Result: workbook-quality behavior map added; non-COM workbook preparation and static contract checks are separated from Excel COM refresh, recalculation, Power Query, and cached-value validation that may require desktop-user or elevated PowerShell.
