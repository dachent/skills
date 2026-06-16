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

## Consumers

- `docx-win`
- `pptx-win`
- `xlsx-win`

## Validation

- Hosted CI parses PowerShell and validates referenced paths.
- Self-hosted `office` runner runs true Word, PowerPoint, and Excel smoke tests.
- Future compatibility tests should cover preflight JSON shape, sandbox-user detection, wrong-session handling, timeout behavior, and cleanup guidance.
