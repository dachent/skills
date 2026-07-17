"""Job schema tests: valid, invalid, unsafe/unknown-field, and version-mismatch manifests.

Covers the original #34 acceptance criterion "Schemas reject unknown and
unsafe fields" and the amendment's "unknown step types are rejected the same
as unknown top-level fields."
"""

from __future__ import annotations

import pytest

from control_plane.errors import ContractError
from control_plane.schemas import JOB_SCHEMA, KNOWN_STEP_TYPES, validate_job

VALID_JOB = {
    "schema_version": "2.0",
    "idempotency_key": "job-001",
    "steps": [
        {"type": "open", "workbook_path": "C:\\jobs\\input\\model.xlsx"},
        {"type": "refresh", "connections": "all"},
        {"type": "recalc"},
    ],
}


def test_valid_job_passes() -> None:
    validate_job(VALID_JOB)  # must not raise


def test_missing_required_field_is_schema_invalid() -> None:
    job = {"schema_version": "2.0", "idempotency_key": "job-002", "steps": [{"type": "open"}]}

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "SCHEMA_INVALID"


def test_unknown_top_level_field_is_rejected() -> None:
    job = {**VALID_JOB, "shell_command": "rm -rf /"}

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "SCHEMA_INVALID"
    assert "additional" in excinfo.value.message.lower()


def test_legacy_operation_field_is_rejected_as_unsafe() -> None:
    # RFC 0001's superseded single-`operation` shape must not silently pass.
    job = {
        "schema_version": "2.0",
        "idempotency_key": "job-003",
        "operation": "refresh_and_calculate",
        "steps": VALID_JOB["steps"],
    }

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "SCHEMA_INVALID"


def test_schema_version_mismatch_is_normalized() -> None:
    job = {**VALID_JOB, "schema_version": "1.0"}

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "MANIFEST_VERSION_MISMATCH"
    assert excinfo.value.details["received"] == "1.0"
    assert excinfo.value.details["expected"] == "2.0"


def test_unknown_step_type_is_rejected() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "job-004",
        "steps": [{"type": "delete_everything", "target": "*"}],
    }

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "UNKNOWN_STEP_TYPE"
    assert excinfo.value.details["step_index"] == 0


def test_refresh_step_accepts_explicit_connection_list() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "job-005",
        "steps": [
            {"type": "open", "workbook_path": "model.xlsx"},
            {"type": "refresh", "connections": ["SalesDB", "InventoryDB"]},
        ],
    }

    validate_job(job)  # must not raise


def test_known_step_types_matches_job_schema_step_definitions() -> None:
    # KNOWN_STEP_TYPES (control_plane/schemas.py) and dry_run.py's step->state
    # dispatch are hand-kept in sync with job.schema.json's step "oneOf" list.
    # This can't stop JSON Schema and Python from drifting apart entirely,
    # but it turns "someone added a 6th step type and forgot the Python side"
    # into a failing test instead of a silent gap.
    step_refs = JOB_SCHEMA["definitions"]["step"]["oneOf"]
    schema_step_types = set()
    for ref in step_refs:
        definition_name = ref["$ref"].rsplit("/", 1)[-1]
        const = JOB_SCHEMA["definitions"][definition_name]["properties"]["type"]["const"]
        schema_step_types.add(const)

    assert schema_step_types == KNOWN_STEP_TYPES


def test_run_approved_macro_rejects_unsafe_name() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "job-006",
        "steps": [{"type": "run_approved_macro", "macro_name": "Shell(\"calc.exe\")"}],
    }

    with pytest.raises(ContractError) as excinfo:
        validate_job(job)

    assert excinfo.value.code == "SCHEMA_INVALID"
