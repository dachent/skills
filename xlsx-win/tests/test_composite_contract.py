"""Contract-only tests for issue #84's versioned composite operations."""

from __future__ import annotations

import copy

import pytest

from control_plane.errors import ContractError
from control_plane.schemas import COMPOSITE_SCHEMA_VERSION, validate_job

_HASHES = {
    "workbook": "a" * 64,
    "source": "b" * 64,
    "schema": "c" * 64,
    "canonical": "d" * 64,
    "oracle": "e" * 64,
}


def _manifest(operation_type: str = "append_table_rows") -> dict:
    append = operation_type == "append_table_rows"
    table = {
        "sheet": "Data",
        "name": "Data",
        "existing_body_rows": 10,
        "final_body_rows": 12 if append else 2,
        "column_count": 3,
        "writable_runs": 2,
        "columns": [
            {"name": "Payment ID", "role": "writable", "logical_type": "text"},
            {"name": "Pmt Date", "role": "calculated", "logical_type": "datetime"},
            {"name": "Amount", "role": "writable", "logical_type": "number"},
        ],
        "filters": "none",
        "totals": False,
        "saved_sort": (
            {
                "column": "Payment ID",
                "direction": "descending",
                "behavior": "preserve_descriptor_do_not_reapply",
            }
            if append
            else None
        ),
    }
    return {
        "schema_version": COMPOSITE_SCHEMA_VERSION,
        "idempotency_key": "issue84-contract-test",
        "steps": [
            {
                "type": operation_type,
                "operation_version": "1.0",
                "workbook_path": "C:\\jobs\\seed.xlsx",
                "workbook_sha256": _HASHES["workbook"],
                "output_path": "C:\\jobs\\output.xlsx",
                "table": table,
                "source": {
                    "path": "C:\\jobs\\rows.csv",
                    "raw_sha256": _HASHES["source"],
                    "schema_path": "C:\\jobs\\rows.schema.json",
                    "schema_sha256": _HASHES["schema"],
                    "canonical_sha256": _HASHES["canonical"],
                    "row_count": 2,
                    "column_count": 3,
                    "encoded_bytes": 100,
                    "text_bytes": 20,
                    "cardinality": [2, 2, 2],
                    "writable_runs": 2,
                },
                "dependent_pivots": {
                    "mode": "linked_only",
                    "profile": "worksheet_simple_v1",
                    "cache_count": 1,
                    "report_count": 3,
                    "oracle_path": "C:\\jobs\\oracle.json",
                    "oracle_sha256": _HASHES["oracle"],
                },
                "capability_profile": "excel64_table_pivot_append_saved_sort_v1",
            }
        ],
        "timeouts": {
            "preflight_seconds": 120,
            "write_seconds": 1800,
            "calculation_seconds": 600,
            "pivot_seconds": 600,
            "save_seconds": 600,
            "reopen_seconds": 600,
            "validation_seconds": 600,
            "close_seconds": 120,
            "whole_job_seconds": 3600,
            "inactivity_seconds": 300,
            "shutdown_seconds": 30,
        },
    }


@pytest.mark.parametrize("operation_type", ["append_table_rows", "replace_table_data"])
def test_composite_operations_validate(operation_type: str) -> None:
    validate_job(_manifest(operation_type))


def test_composite_contract_rejects_multiple_operations() -> None:
    manifest = _manifest()
    manifest["steps"].append(copy.deepcopy(manifest["steps"][0]))

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "SCHEMA_INVALID"


def test_append_row_arithmetic_is_fail_closed() -> None:
    manifest = _manifest()
    manifest["steps"][0]["table"]["final_body_rows"] = 11

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"


def test_composite_column_counts_must_agree() -> None:
    manifest = _manifest()
    manifest["steps"][0]["source"]["column_count"] = 2

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"


def test_composite_writable_runs_are_recomputed() -> None:
    manifest = _manifest()
    manifest["steps"][0]["source"]["writable_runs"] = 1

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"


def test_seed_and_output_must_be_distinct() -> None:
    manifest = _manifest()
    manifest["steps"][0]["output_path"] = manifest["steps"][0]["workbook_path"]

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"


def test_replacement_profile_rejects_saved_sort() -> None:
    manifest = _manifest("replace_table_data")
    manifest["steps"][0]["table"]["saved_sort"] = {
        "column": "Payment ID",
        "direction": "descending",
        "behavior": "preserve_descriptor_do_not_reapply",
    }

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"


def test_whole_job_timeout_cannot_preempt_a_phase() -> None:
    manifest = _manifest()
    manifest["timeouts"]["whole_job_seconds"] = 900

    with pytest.raises(ContractError) as excinfo:
        validate_job(manifest)

    assert excinfo.value.code == "COMPOSITE_SEMANTICS_INVALID"
