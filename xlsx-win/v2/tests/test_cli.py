"""CLI tests: `validate` and `dry-run` must both work with no Excel installed.

Covers the original #34 acceptance criterion "CLI can validate and dry-run
manifests without Excel" and the amendment's "CLI dry-run validates a
multi-step manifest without Excel and reports which step, if any, is
structurally invalid."
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from wb_fixtures import save_workbook

from control_plane.cli import main

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLI_PATH = Path(__file__).resolve().parent.parent / "control_plane" / "cli.py"


def _run_main(capsys, argv: list) -> tuple:
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, json.loads(captured.out)


def test_validate_accepts_a_valid_manifest(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["validate", str(FIXTURES / "valid_job.json")])

    assert exit_code == 0
    assert payload == {"valid": True}


def test_validate_reports_a_schema_violation(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["validate", str(FIXTURES / "invalid_missing_field.json")])

    assert exit_code == 1
    assert payload["valid"] is False
    assert payload["error"]["code"] == "SCHEMA_INVALID"


def test_validate_reports_an_unsafe_top_level_field(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["validate", str(FIXTURES / "unsafe_extra_field.json")])

    assert exit_code == 1
    assert payload["error"]["code"] == "SCHEMA_INVALID"


def test_validate_reports_a_version_mismatch(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["validate", str(FIXTURES / "version_mismatch.json")])

    assert exit_code == 1
    assert payload["error"]["code"] == "MANIFEST_VERSION_MISMATCH"


def test_dry_run_prints_the_full_state_sequence_for_a_valid_manifest(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["dry-run", str(FIXTURES / "valid_job.json")])

    assert exit_code == 0
    assert payload["valid"] is True
    assert payload["states"][0] == "QUEUED"
    assert payload["states"][-1] == "SUCCEEDED"
    assert "CALCULATING" in payload["states"]


def test_dry_run_reports_which_step_is_structurally_invalid(capsys) -> None:
    exit_code, payload = _run_main(
        capsys, ["dry-run", str(FIXTURES / "invalid_step_in_multistep.json")]
    )

    assert exit_code == 1
    assert payload["error"]["code"] == "SCHEMA_INVALID"
    # steps[1] is the malformed refresh step (missing "connections").
    assert payload["error"]["details"]["json_path"] == ["steps", 1]


def test_validate_reports_missing_manifest_file(capsys) -> None:
    exit_code, payload = _run_main(capsys, ["validate", str(FIXTURES / "does_not_exist.json")])

    assert exit_code == 1
    assert payload["error"]["code"] == "SCHEMA_INVALID"


def test_validate_contract_reports_passing_invariants_as_json(tmp_path, capsys) -> None:
    workbook_path = save_workbook(
        tmp_path / "wb.xlsx", lambda wb: wb.active.__setitem__("A1", "OK")
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps(
            {
                "sentinel_cells": [{"sheet": "Sheet", "cell": "A1", "expected": "OK"}],
                "prohibit_visible_errors": False,
            }
        )
    )

    exit_code, payload = _run_main(
        capsys, ["validate-contract", str(workbook_path), str(contract_path)]
    )

    assert exit_code == 0
    assert payload["all_passed"] is True
    assert payload["invariants"] == [
        {"name": "sentinel_cell:Sheet!A1", "passed": True}
    ]


def test_validate_contract_reports_a_failed_invariant_with_exit_code_2(tmp_path, capsys) -> None:
    workbook_path = save_workbook(
        tmp_path / "wb.xlsx", lambda wb: wb.active.__setitem__("A1", "NOT_OK")
    )
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(
        json.dumps({"sentinel_cells": [{"sheet": "Sheet", "cell": "A1", "expected": "OK"}]})
    )

    exit_code, payload = _run_main(
        capsys, ["validate-contract", str(workbook_path), str(contract_path)]
    )

    assert exit_code == 2
    assert payload["all_passed"] is False
    assert payload["invariants"][0]["passed"] is False


def test_validate_contract_reports_a_malformed_contract_as_an_error(tmp_path, capsys) -> None:
    workbook_path = save_workbook(tmp_path / "wb.xlsx", lambda wb: None)
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps({"required_sheets": "not-a-list"}))

    exit_code, payload = _run_main(
        capsys, ["validate-contract", str(workbook_path), str(contract_path)]
    )

    assert exit_code == 1
    assert payload["error"]["code"] == "SCHEMA_INVALID"


def test_cli_is_directly_runnable_as_a_script_with_no_excel_installed() -> None:
    # Proves the file at xlsx-win/v2/control_plane/cli.py is itself the
    # entrypoint (not just importable), and that its whole import chain has
    # no Excel/COM/openpyxl dependency: this subprocess has none installed.
    completed = subprocess.run(
        [sys.executable, str(CLI_PATH), "validate", str(FIXTURES / "valid_job.json")],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {"valid": True}
