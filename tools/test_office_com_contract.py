from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def require_contains(text: str, expected: str, context: str, failures: list[str]) -> None:
    if expected not in text:
        failures.append(f"{context}: missing expected text: {expected}")


def require_file(relative_path: str, failures: list[str]) -> None:
    if not (REPO_ROOT / relative_path).is_file():
        failures.append(f"missing file: {relative_path}")


def validate_shared_runtime(failures: list[str]) -> None:
    contract = read(".shared/office-com/CONTRACT.md")
    common = read(".shared/office-com/scripts/office_com_common.psm1")
    preflight = read(".shared/office-com/scripts/office_com_preflight.ps1")

    for expected in [
        "## Design Upskill Contribution",
        "## COM Boundary",
        "Normal Codex execution can perform documentation edits",
        "True Office open/save/render/recalculate/export validation belongs",
        "self-hosted `office` runner",
    ]:
        require_contains(contract, expected, ".shared/office-com/CONTRACT.md", failures)

    for expected in [
        "function Get-OfficeComPreflightResult",
        "function Assert-OfficeComAvailable",
        "function Get-OfficePreflightFailureInfo",
        "function Invoke-ChildPowerShellScript",
        "can_use_com",
        "office_com_wrong_session",
        "office_com_sandbox_user",
        "interactive_session_required",
        "0x80070520",
    ]:
        require_contains(common, expected, ".shared/office-com/scripts/office_com_common.psm1", failures)

    for expected in [
        "Get-OfficeComPreflightResult",
        "ConvertTo-Json -Depth 8",
        "exit 0",
        "exit 2",
    ]:
        require_contains(preflight, expected, ".shared/office-com/scripts/office_com_preflight.ps1", failures)


def validate_impacted_skills(failures: list[str]) -> None:
    required_files = [
        "docx-win/references/document-quality-map.md",
        "xlsx-win/references/workbook-quality-map.md",
        "docx-win/PROVENANCE.md",
        "xlsx-win/PROVENANCE.md",
    ]
    for relative_path in required_files:
        require_file(relative_path, failures)

    checks = [
        (
            "docx-win/SKILL.md",
            [
                "## Design Upskill Contribution",
                "references/document-quality-map.md",
                "layout fidelity",
                "PDF evidence",
            ],
        ),
        (
            "xlsx-win/SKILL.md",
            [
                "## Design Upskill Contribution",
                "references/workbook-quality-map.md",
                "chart-ready data",
                "calculation correctness",
            ],
        ),
        (
            "docx-win/PROVENANCE.md",
            [
                "Codex Phase 3 Office runtime alignment pass",
                "document-quality behavior map",
                "desktop-user or elevated PowerShell",
            ],
        ),
        (
            "xlsx-win/PROVENANCE.md",
            [
                "Codex Phase 3 Office runtime alignment pass",
                "workbook-quality behavior map",
                "desktop-user or elevated PowerShell",
            ],
        ),
    ]
    for relative_path, expected_items in checks:
        text = read(relative_path)
        for expected in expected_items:
            require_contains(text, expected, relative_path, failures)


def validate_workflows(failures: list[str]) -> None:
    office_smoke = read(".github/workflows/office-smoke.yml")
    validate = read(".github/workflows/validate.yml")

    for expected in [
        "workflow_dispatch:",
        "ref:",
        "self-hosted",
        "windows",
        "office",
        ".\\docx-win\\scripts\\smoke-test.ps1",
        ".\\pptx-win\\scripts\\smoke_test.ps1",
        ".\\xlsx-win\\scripts\\self_test_xlsx_win.ps1",
        "office-smoke-summary.json",
        "exit_code",
    ]:
        require_contains(office_smoke, expected, ".github/workflows/office-smoke.yml", failures)

    require_contains(
        validate,
        "python .\\tools\\test_office_com_contract.py",
        ".github/workflows/validate.yml",
        failures,
    )


def main() -> int:
    failures: list[str] = []
    validate_shared_runtime(failures)
    validate_impacted_skills(failures)
    validate_workflows(failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Office COM contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
