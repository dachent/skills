# Office COM Shared Runtime Contract

`.shared/office-com` is the shared Windows Office COM preflight and helper layer used by `docx-win`, `pptx-win`, and `xlsx-win`.

## Supported Environment

- Windows with an active interactive desktop session.
- Microsoft 365 desktop apps installed for the requested Office application.
- PowerShell available as `pwsh` or Windows PowerShell.
- True Office COM work runs from the signed-in desktop user session or an Office-capable self-hosted runner.

## Design Upskill Contribution

No-template design work needs rendered evidence. Word documents, PowerPoint decks, and Excel workbooks cannot be fully verified by package inspection alone because pagination, text bounds, chart rendering, cached values, and export fidelity depend on the desktop Office applications. This shared runtime defines when Codex can proceed normally, when it must reroute to a COM-capable context, and how to classify environment failures separately from artifact failures.

## Contract

- `scripts/office_com_preflight.ps1` returns JSON and exits `0` only when requested Office COM apps are available from the current session.
- `scripts/office_com_preflight.ps1` exits nonzero when COM is unavailable or the shell is unsuitable.
- `scripts/office_com_common.psm1` normalizes wrong-session, missing-Office, busy-Office, and runtime errors into stable `error_kind` values.
- Skill wrappers must call preflight before creating Word, PowerPoint, or Excel COM objects.
- Skill wrappers must treat `0x80070520` and `office_com_wrong_session` as environment/session failures, not document/workbook/deck failures.
- COM automation scripts must close documents/presentations/workbooks, quit applications, and release COM objects in cleanup paths.

## COM Boundary

Normal Codex execution can perform documentation edits, static PowerShell parsing, Python/Node checks, and non-instantiating contract tests. True Office open/save/render/recalculate/export validation belongs in desktop-user or elevated PowerShell, or in the self-hosted `office` runner.

### Non-COM work

Codex can safely do these tasks without creating Office COM objects:

- edit skill documentation, reference maps, provenance files, and workflow YAML;
- parse PowerShell and Python helper scripts;
- inspect OOXML package structure with file libraries;
- prepare source text, tables, images, formulas, M definitions, and test fixtures;
- run `tools/test_office_com_contract.py` to check that the shared runtime contract is still documented and wired into CI.

### COM-required work

Move these tasks to the signed-in desktop-user PowerShell session, an elevated PowerShell session when the environment requires it, or the self-hosted Office runner:

- Word open/save, tracked changes, comments, field refresh, pagination, legacy conversion, and PDF export;
- PowerPoint render, screenshot, PDF export, text-bound checks, and animation/media smoke tests;
- Excel refresh, full calculation rebuild, async Power Query completion, Data Model or PivotTable state, and saved cached-value verification;
- cleanup verification for orphaned Office processes after a failed automation run.

The split is intentional: it lets Codex keep reasoning and static validation in the normal sandbox while reserving fidelity claims for real desktop Office.

## Consumers

- `docx-win`
- `pptx-win`
- `xlsx-win`

## Validation

- Hosted CI parses PowerShell and validates referenced paths.
- Hosted CI runs `tools/test_office_com_contract.py`, which does not instantiate Office.
- Self-hosted `office` runner runs true Word, PowerPoint, and Excel smoke tests.
- Future compatibility tests should cover preflight JSON shape, sandbox-user detection, wrong-session handling, timeout behavior, and cleanup guidance.
