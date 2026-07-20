from __future__ import annotations

import copy

import pytest

from control_plane.errors import ContractError
from control_plane.result_contract import (
    build_composite_result,
    publication_eligible,
    required_composite_invariants,
    validate_composite_result,
)


HASH = "a" * 64
COMMIT = "b" * 40


def _invariants(operation: str) -> list[dict]:
    return [
        {"name": name, "version": "1.0", "passed": True, "evidence_sha256": HASH}
        for name in sorted(required_composite_invariants(operation))
    ]


def _result(operation: str = "replace_table_data", *, published: bool = True) -> dict:
    return build_composite_result(
        run_id="run-1",
        idempotency_key="job-1",
        operation=operation,
        final_state="SUCCEEDED",
        steps=[{"step_index": 0, "type": operation, "status": "succeeded", "evidence_sha256": HASH}],
        invariants=_invariants(operation),
        bindings={name: HASH for name in ("workbook", "source", "schema", "plan", "staged_output", "verifier", "evidence")},
        profile={"id": "profile-v1", "sha256": HASH, "build_commit": COMMIT},
        cleanup={
            "owned_processes_zero": True,
            "worker_exit_verified": True,
            "excel_exit_verified": True,
            "termination_verified": True,
        },
        publication={
            "status": "published" if published else "not_attempted",
            "atomic": published,
            "staged_sha256": HASH,
            "destination_sha256": HASH if published else "0" * 64,
        },
    )


@pytest.mark.parametrize("operation", ["append_table_rows", "replace_table_data"])
def test_exact_published_proof_computes_ok(operation: str) -> None:
    result = _result(operation)
    assert result["ok"] is True
    validate_composite_result(result)


def test_prepublication_proof_is_eligible_but_not_ok() -> None:
    result = _result(published=False)
    assert result["ok"] is False
    assert publication_eligible(result) is True


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "unexpected", "failed", "wrong_version"])
def test_invariant_registry_fails_closed(mutation: str) -> None:
    result = _result()
    result["ok"] = False
    if mutation == "missing":
        result["invariants"].pop()
    elif mutation == "duplicate":
        result["invariants"][-1] = copy.deepcopy(result["invariants"][0])
    elif mutation == "unexpected":
        result["invariants"][-1]["name"] = "producer_says_it_is_fine"
    elif mutation == "failed":
        result["invariants"][0]["passed"] = False
    else:
        result["invariants"][0]["version"] = "9.9"

    with pytest.raises(ContractError) as excinfo:
        validate_composite_result(result)
    assert excinfo.value.code in {"RESULT_PROOF_INVALID", "SCHEMA_INVALID"}


def test_producer_cannot_assert_ok_before_publication() -> None:
    result = _result(published=False)
    result["ok"] = True
    with pytest.raises(ContractError) as excinfo:
        validate_composite_result(result)
    assert excinfo.value.code == "RESULT_PROOF_INVALID"


@pytest.mark.parametrize("field", ["owned_processes_zero", "worker_exit_verified", "excel_exit_verified", "termination_verified"])
def test_cleanup_is_part_of_success(field: str) -> None:
    result = _result()
    result["cleanup"][field] = False
    result["ok"] = False
    with pytest.raises(ContractError) as excinfo:
        validate_composite_result(result)
    assert excinfo.value.code == "RESULT_PROOF_INVALID"


def test_published_hash_must_equal_verified_stage_and_binding() -> None:
    result = _result()
    result["publication"]["destination_sha256"] = "c" * 64
    result["ok"] = False
    with pytest.raises(ContractError) as excinfo:
        validate_composite_result(result)
    assert excinfo.value.code == "RESULT_PROOF_INVALID"
