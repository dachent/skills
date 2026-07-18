"""Tests for the `run` subcommand (issue #71).

Covers the two failure paths that must work with no Excel installed --
manifest validation failure (must never reach executable resolution) and
executable-not-found failure (a clear FileNotFoundError-derived message,
no Excel launched) -- plus one real end-to-end invocation gated behind
XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1, reusing
certification/excel_safety.py's existing preflight/postflight pattern per
this issue's own safety rules rather than reinventing it.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest
from wb_fixtures import save_workbook

from control_plane.cli import main
from control_plane.supervisor_runner import SUPERVISOR_PATH_ENV_VAR, WORKER_PATH_ENV_VAR

_CERT_ROOT = Path(__file__).resolve().parent.parent / "certification"
if str(_CERT_ROOT) not in sys.path:
    sys.path.insert(0, str(_CERT_ROOT))

import excel_safety  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _run_main(capsys, argv: list) -> tuple:
    exit_code = main(argv)
    captured = capsys.readouterr()
    return exit_code, json.loads(captured.out)


def _point_exe_env_vars_at_nonexistent_files(monkeypatch, tmp_path) -> None:
    # Forces find_built_exe to fail fast (FileNotFoundError) rather than
    # depending on whether real built .exe files happen to exist under
    # supervisor/**/bin/** on the machine running this test -- deterministic
    # either way, and never launches anything.
    monkeypatch.setenv(SUPERVISOR_PATH_ENV_VAR, str(tmp_path / "no_such_supervisor.exe"))
    monkeypatch.setenv(WORKER_PATH_ENV_VAR, str(tmp_path / "no_such_worker.exe"))


def test_run_rejects_an_invalid_manifest_before_resolving_the_supervisor(
    tmp_path, capsys, monkeypatch
) -> None:
    _point_exe_env_vars_at_nonexistent_files(monkeypatch, tmp_path)

    exit_code, payload = _run_main(capsys, ["run", str(FIXTURES / "invalid_missing_field.json")])

    # Same shape/code as `validate` against the identical fixture -- proves
    # `run` did not reach executable resolution at all (if it had, the
    # nonexistent-exe env vars above would have produced a different error).
    assert exit_code == 1
    assert payload["valid"] is False
    assert payload["error"]["code"] == "SCHEMA_INVALID"


def test_run_rejects_a_manifest_with_an_unknown_step_type_before_resolving_the_supervisor(
    tmp_path, capsys, monkeypatch
) -> None:
    _point_exe_env_vars_at_nonexistent_files(monkeypatch, tmp_path)

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-unknown-step",
                "steps": [{"type": "not_a_real_step_type"}],
            }
        )
    )

    exit_code, payload = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 1
    assert payload["error"]["code"] == "UNKNOWN_STEP_TYPE"
    assert not (tmp_path / "job.events.jsonl").exists()
    assert not (tmp_path / "job.result.json").exists()


def test_run_reports_a_clear_error_when_the_supervisor_executable_is_not_found(
    tmp_path, capsys, monkeypatch
) -> None:
    _point_exe_env_vars_at_nonexistent_files(monkeypatch, tmp_path)

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-missing-exe",
                "steps": [{"type": "recalc"}],
            }
        )
    )

    exit_code, payload = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 1
    assert payload["valid"] is False
    assert payload["error"]["code"] == "SUPERVISOR_INVOCATION_FAILED"
    assert "no_such_supervisor.exe" in payload["error"]["message"]
    assert "does not exist" in payload["error"]["message"]
    # No result/events files -- the supervisor process was never launched.
    assert not (tmp_path / "job.events.jsonl").exists()
    assert not (tmp_path / "job.result.json").exists()


def test_run_honors_explicit_events_and_result_paths(tmp_path, capsys, monkeypatch) -> None:
    _point_exe_env_vars_at_nonexistent_files(monkeypatch, tmp_path)

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-explicit-paths",
                "steps": [{"type": "recalc"}],
            }
        )
    )
    events_path = tmp_path / "custom.events.jsonl"
    result_path = tmp_path / "custom.result.json"

    exit_code, payload = _run_main(
        capsys,
        ["run", str(manifest_path), "--events", str(events_path), "--result", str(result_path)],
    )

    assert exit_code == 1
    assert payload["error"]["details"]["events_path"] == str(events_path)
    assert payload["error"]["details"]["result_path"] == str(result_path)


@pytest.mark.skipif(
    os.environ.get(excel_safety.RUN_ENV_VAR) != "1",
    reason=f"Set {excel_safety.RUN_ENV_VAR}=1 to run this real-Excel end-to-end test.",
)
def test_run_end_to_end_against_real_excel(tmp_path) -> None:
    excel_safety.preflight_or_raise()

    workbook_path = save_workbook(
        tmp_path / "input.xlsx", lambda wb: wb.active.__setitem__("A1", 1)
    )
    output_path = tmp_path / "output.xlsx"
    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-run-e2e",
                "steps": [
                    {"type": "open", "workbook_path": str(workbook_path)},
                    {"type": "recalc"},
                    {"type": "save_as", "output_path": str(output_path), "overwrite": True},
                ],
            }
        )
    )

    try:
        exit_code = main(["run", str(manifest_path)])
    finally:
        excel_safety.assert_no_excel_survives()

    result_path = tmp_path / "job.result.json"
    assert result_path.exists()
    result_doc = json.loads(result_path.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert result_doc["ok"] is True
    assert result_doc["final_state"] == "SUCCEEDED"
    assert output_path.exists()
