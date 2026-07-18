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


def test_run_stages_the_open_steps_workbook_path_before_invoking_the_supervisor(
    tmp_path, capsys, monkeypatch
) -> None:
    """Issue #72 / RFC 0002 decision 9: the open step's workbook_path must be
    staged into a fresh local temp copy, and the *staged* copy's path -- not
    the manifest's original, real input path -- is what actually gets handed
    to the supervisor. The original input file itself is never modified."""
    import control_plane.cli as cli_module

    original_input = tmp_path / "input.xlsx"
    original_input.write_bytes(b"original-workbook-bytes")

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-staging",
                "steps": [
                    {"type": "open", "workbook_path": str(original_input)},
                    {"type": "recalc"},
                ],
            }
        )
    )

    captured: dict = {}

    class _FakeRunResult:
        exit_code = 0
        stdout = ""
        stderr = ""

    def _fake_run_supervisor(job_path, events_path, result_path, hard_timeout_seconds, extra_env=None):
        captured["job_path"] = Path(job_path)
        return _FakeRunResult()

    monkeypatch.setattr(cli_module, "run_supervisor", _fake_run_supervisor)

    exit_code, _ = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 0
    staged_manifest_path = captured["job_path"]
    assert staged_manifest_path != manifest_path

    staged_job = json.loads(staged_manifest_path.read_text(encoding="utf-8"))
    staged_workbook_path = Path(staged_job["steps"][0]["workbook_path"])

    assert staged_workbook_path != original_input
    assert staged_workbook_path.read_bytes() == b"original-workbook-bytes"
    # The real input path is never touched -- still exactly what it was.
    assert original_input.read_bytes() == b"original-workbook-bytes"


def test_run_does_not_stage_a_manifest_with_no_open_step(tmp_path, capsys, monkeypatch) -> None:
    """A manifest with no `open` step has nothing for staging to protect --
    `run` must invoke the supervisor against the caller's original on-disk
    manifest path unchanged, exactly as issue #71 did before staging existed."""
    import control_plane.cli as cli_module

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-no-open-step",
                "steps": [{"type": "recalc"}],
            }
        )
    )

    captured: dict = {}

    class _FakeRunResult:
        exit_code = 0
        stdout = ""
        stderr = ""

    def _fake_run_supervisor(job_path, events_path, result_path, hard_timeout_seconds, extra_env=None):
        captured["job_path"] = Path(job_path)
        return _FakeRunResult()

    monkeypatch.setattr(cli_module, "run_supervisor", _fake_run_supervisor)

    exit_code, _ = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 0
    assert captured["job_path"] == manifest_path


def test_run_publishes_a_staged_save_as_output_only_after_a_successful_result(
    tmp_path, capsys, monkeypatch
) -> None:
    """Issue #72 / RFC 0002 decision 9: the save_as step's output_path is
    staged too, and the real target only gets written via staging.publish
    once the supervisor's own result document reports ok: true."""
    import control_plane.cli as cli_module

    original_input = tmp_path / "input.xlsx"
    original_input.write_bytes(b"input-bytes")
    original_output = tmp_path / "output.xlsx"

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-staging-publish",
                "steps": [
                    {"type": "open", "workbook_path": str(original_input)},
                    {"type": "save_as", "output_path": str(original_output), "overwrite": True},
                ],
            }
        )
    )

    def _fake_run_supervisor(job_path, events_path, result_path, hard_timeout_seconds, extra_env=None):
        staged_job = json.loads(Path(job_path).read_text(encoding="utf-8"))
        staged_output_path = Path(staged_job["steps"][1]["output_path"])
        assert staged_output_path != original_output  # supervisor never sees the real target
        # Simulate the real supervisor/worker: it writes the save_as step's
        # *staged* output_path, never the manifest's original output_path.
        staged_output_path.write_bytes(b"produced-output-bytes")
        Path(result_path).write_text(
            json.dumps({"ok": True, "final_state": "SUCCEEDED"}), encoding="utf-8"
        )

        class _Result:
            exit_code = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(cli_module, "run_supervisor", _fake_run_supervisor)

    exit_code, _ = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 0
    assert original_output.exists()
    assert original_output.read_bytes() == b"produced-output-bytes"


def test_run_publishes_two_save_as_steps_with_colliding_basenames_to_distinct_targets(
    tmp_path, capsys, monkeypatch
) -> None:
    """Regression test for issue #72 review finding (blocker): two save_as
    steps whose output_path values share a basename but live in different
    directories must each be staged to their own distinct staged path, and
    each must end up publishing its own distinct content to its own real
    target -- never cross-contaminating one target with the other step's
    content, and never failing the second publish with STAGING_INVALID
    because the first publish's os.replace already consumed a shared staged
    file."""
    import control_plane.cli as cli_module

    original_input = tmp_path / "input.xlsx"
    original_input.write_bytes(b"input-bytes")

    dir_a = tmp_path / "dirA"
    dir_b = tmp_path / "dirB"
    dir_a.mkdir()
    dir_b.mkdir()
    original_output_a = dir_a / "output.xlsx"
    original_output_b = dir_b / "output.xlsx"

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-staging-colliding-basenames",
                "steps": [
                    {"type": "open", "workbook_path": str(original_input)},
                    {"type": "save_as", "output_path": str(original_output_a), "overwrite": True},
                    {"type": "save_as", "output_path": str(original_output_b), "overwrite": True},
                ],
            }
        )
    )

    def _fake_run_supervisor(job_path, events_path, result_path, hard_timeout_seconds, extra_env=None):
        staged_job = json.loads(Path(job_path).read_text(encoding="utf-8"))
        staged_output_path_a = Path(staged_job["steps"][1]["output_path"])
        staged_output_path_b = Path(staged_job["steps"][2]["output_path"])
        # The two staged paths must not collide even though the real
        # targets share a basename.
        assert staged_output_path_a != staged_output_path_b
        staged_output_path_a.write_bytes(b"CONTENT-FOR-A")
        staged_output_path_b.write_bytes(b"CONTENT-FOR-B")
        Path(result_path).write_text(
            json.dumps({"ok": True, "final_state": "SUCCEEDED"}), encoding="utf-8"
        )

        class _Result:
            exit_code = 0
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(cli_module, "run_supervisor", _fake_run_supervisor)

    exit_code, _ = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 0
    assert original_output_a.exists()
    assert original_output_b.exists()
    assert original_output_a.read_bytes() == b"CONTENT-FOR-A"
    assert original_output_b.read_bytes() == b"CONTENT-FOR-B"


def test_run_does_not_publish_when_the_result_reports_failure(tmp_path, capsys, monkeypatch) -> None:
    """If the job fails, the staged save_as output must never be published --
    the original output_path is left completely untouched (RFC 0002
    decision 9's whole point)."""
    import control_plane.cli as cli_module

    original_input = tmp_path / "input.xlsx"
    original_input.write_bytes(b"input-bytes")
    original_output = tmp_path / "output.xlsx"

    manifest_path = tmp_path / "job.json"
    manifest_path.write_text(
        json.dumps(
            {
                "schema_version": "2.0",
                "idempotency_key": "test-staging-no-publish",
                "steps": [
                    {"type": "open", "workbook_path": str(original_input)},
                    {"type": "save_as", "output_path": str(original_output), "overwrite": True},
                ],
            }
        )
    )

    def _fake_run_supervisor(job_path, events_path, result_path, hard_timeout_seconds, extra_env=None):
        staged_job = json.loads(Path(job_path).read_text(encoding="utf-8"))
        staged_output_path = Path(staged_job["steps"][1]["output_path"])
        staged_output_path.write_bytes(b"partial-output-bytes")
        Path(result_path).write_text(
            json.dumps({"ok": False, "final_state": "FAILED"}), encoding="utf-8"
        )

        class _Result:
            exit_code = 1
            stdout = ""
            stderr = ""

        return _Result()

    monkeypatch.setattr(cli_module, "run_supervisor", _fake_run_supervisor)

    exit_code, _ = _run_main(capsys, ["run", str(manifest_path)])

    assert exit_code == 1
    assert not original_output.exists()


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
