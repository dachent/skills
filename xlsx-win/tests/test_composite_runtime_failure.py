from __future__ import annotations

import pytest

from control_plane.composite_runtime import _raise_for_native_outcome
from control_plane.errors import ContractError
from control_plane.schemas import validate_result


def _native_cleanup_failure() -> dict:
    message = (
        "Worker result was trustworthy but 1 owned process(es) remained; "
        "termination_verified=true; owned_processes_zero=true"
    )
    return {
        "schema_version": "2.0",
        "run_id": "native-cleanup-failure",
        "idempotency_key": "job-native-cleanup-failure",
        "final_state": "FAILED",
        "steps": [
            {"step_index": 0, "type": "append_table_rows", "status": "succeeded"},
            {
                "step_index": -1,
                "type": "supervisor",
                "status": "failed",
                "message": message,
                "error": {
                    "code": "OWNED_PROCESS_CLEANUP_REQUIRED",
                    "message": message,
                    "details": {"cleanup_verified": True},
                },
            },
        ],
        "invariants": [
            {
                "name": "supervisor_owned_process_cleanup",
                "passed": True,
                "message": "termination_verified=true; owned_processes_zero=true",
            }
        ],
        "ok": False,
    }


def test_trustworthy_native_cleanup_failure_preserves_original_error() -> None:
    native_result = _native_cleanup_failure()
    validate_result(native_result)

    with pytest.raises(ContractError) as excinfo:
        _raise_for_native_outcome(native_result, launch_exit_code=1)

    assert excinfo.value.code == "OWNED_PROCESS_CLEANUP_REQUIRED"
    assert excinfo.value.message == native_result["steps"][1]["error"]["message"]
    assert excinfo.value.details == {"cleanup_verified": True}


def test_inconsistent_native_result_remains_result_proof_invalid() -> None:
    native_result = _native_cleanup_failure()
    native_result["ok"] = True

    with pytest.raises(ContractError) as excinfo:
        _raise_for_native_outcome(native_result, launch_exit_code=1)

    assert excinfo.value.code == "RESULT_PROOF_INVALID"
