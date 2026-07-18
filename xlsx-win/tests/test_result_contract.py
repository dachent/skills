"""Result contract tests: `ok` is computed, never an independently-settable input.

Covers RFC 0002 decision 5 / the amendment's updated acceptance criterion:
"Result schema has a top-level ok: boolean, computed from the other fields
(not independently settable) -- true iff every step succeeded and every
declared invariant (if any) passed."
"""

from __future__ import annotations

import inspect

import pytest

from control_plane.errors import ContractError
from control_plane.result_contract import build_result, compute_ok


def _step(status: str, step_index: int = 0, step_type: str = "recalc") -> dict:
    return {"step_index": step_index, "type": step_type, "status": status}


def test_build_result_has_no_ok_parameter() -> None:
    # Structurally impossible to pass ok in: there is no such parameter.
    assert "ok" not in inspect.signature(build_result).parameters


def test_ok_is_true_when_all_steps_succeed_and_no_invariants_declared() -> None:
    result = build_result(
        run_id="run-1",
        idempotency_key="job-1",
        final_state="SUCCEEDED",
        steps=[_step("succeeded", 0), _step("succeeded", 1)],
    )

    assert result["ok"] is True
    assert result["invariants"] == []


def test_ok_is_false_when_any_step_fails() -> None:
    result = build_result(
        run_id="run-2",
        idempotency_key="job-2",
        final_state="FAILED",
        steps=[_step("succeeded", 0), _step("failed", 1)],
    )

    assert result["ok"] is False


def test_ok_is_false_when_a_declared_invariant_fails_even_if_all_steps_succeed() -> None:
    result = build_result(
        run_id="run-3",
        idempotency_key="job-3",
        final_state="SUCCEEDED",
        steps=[_step("succeeded", 0)],
        invariants=[{"name": "row_count_minimum", "passed": False}],
    )

    assert result["ok"] is False


def test_ok_is_true_when_all_steps_and_invariants_pass() -> None:
    result = build_result(
        run_id="run-4",
        idempotency_key="job-4",
        final_state="SUCCEEDED",
        steps=[_step("succeeded", 0)],
        invariants=[{"name": "row_count_minimum", "passed": True}],
    )

    assert result["ok"] is True


def test_compute_ok_matches_build_result() -> None:
    steps = [_step("succeeded", 0)]
    invariants = [{"name": "freshness_window", "passed": True}]
    assert compute_ok(steps, invariants) is True

    result = build_result(
        run_id="run-5", idempotency_key="job-5", final_state="SUCCEEDED", steps=steps, invariants=invariants
    )
    assert result["ok"] == compute_ok(steps, invariants)


def test_build_result_validates_against_the_result_schema() -> None:
    with pytest.raises(ContractError) as excinfo:
        build_result(
            run_id="",  # violates minLength: 1
            idempotency_key="job-6",
            final_state="SUCCEEDED",
            steps=[_step("succeeded", 0)],
        )

    assert excinfo.value.code == "SCHEMA_INVALID"


def test_build_result_rejects_non_terminal_final_state() -> None:
    with pytest.raises(ContractError):
        build_result(
            run_id="run-7",
            idempotency_key="job-7",
            final_state="CALCULATING",  # not a terminal state
            steps=[_step("succeeded", 0)],
        )
