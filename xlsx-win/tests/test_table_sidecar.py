from __future__ import annotations

import csv
import hashlib
import json

import pytest

from control_plane.errors import ContractError
from control_plane.table_sidecar import inspect_sidecar, iter_typed_rows, load_sidecar_schema, verify_source_binding


def _schema() -> dict:
    return {
        "schema_version": "1.0",
        "encoding": "utf-8",
        "delimiter": ",",
        "quotechar": '"',
        "has_header": True,
        "date_system": "1900",
        "columns": [
            {"id": 1, "name": "Id", "role": "writable", "logical_type": "text", "storage_type": "inline_string", "number_format": None},
            {"id": 2, "name": "Amount", "role": "writable", "logical_type": "number", "storage_type": "number", "number_format": None},
            {"id": 3, "name": "When", "role": "writable", "logical_type": "datetime", "storage_type": "number", "number_format": "m/d/yyyy"},
            {"id": 4, "name": "Flag", "role": "writable", "logical_type": "boolean", "storage_type": "boolean", "number_format": None},
            {"id": 5, "name": "Formula", "role": "calculated", "logical_type": "number", "storage_type": "number", "number_format": None},
        ],
    }


def _write_fixture(tmp_path, rows: list[list[str]] | None = None):
    schema_path = tmp_path / "rows.schema.json"
    csv_path = tmp_path / "rows.csv"
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["Id", "Amount", "When", "Flag", "Formula"])
        writer.writerows(rows or [["001", "12.50", "45292", "TRUE", ""], ["=literal", "-0", "45293.5", "FALSE", ""]])
    return csv_path, schema_path


def test_streaming_typed_stats_and_formula_like_text(tmp_path) -> None:
    csv_path, schema_path = _write_fixture(tmp_path)
    schema = load_sidecar_schema(schema_path)
    rows = list(iter_typed_rows(csv_path, schema))
    stats = inspect_sidecar(csv_path, schema_path, scratch_dir=tmp_path)
    assert rows[1][0].normalized == "=literal"
    assert rows[1][0].storage_type == "inline_string"
    assert rows[0][1].normalized == "12.5"
    assert rows[1][1].normalized == "0"
    assert stats.row_count == 2
    assert stats.column_count == 5
    assert stats.cardinality == (2, 2, 2, 2, 0)
    assert stats.writable_runs == 1
    assert not list(tmp_path.glob("*.sqlite"))


def test_source_binding_is_exact(tmp_path) -> None:
    csv_path, schema_path = _write_fixture(tmp_path)
    stats = inspect_sidecar(csv_path, schema_path, scratch_dir=tmp_path)
    operation = {"source": stats.to_dict() | {"path": str(csv_path), "schema_path": str(schema_path)}}
    verify_source_binding(operation, stats)
    operation["source"]["row_count"] += 1
    with pytest.raises(ContractError) as excinfo:
        verify_source_binding(operation, stats)
    assert excinfo.value.code == "SOURCE_BINDING_MISMATCH"


@pytest.mark.parametrize(
    "rows",
    [
        [["id", "1234567890123456", "45292", "TRUE", ""]],
        [["id", "NaN", "45292", "TRUE", ""]],
        [["id", "1", "45292", "true", ""]],
        [["id", "1", "45292", "TRUE", "not-empty"]],
    ],
)
def test_unsupported_or_ambiguous_values_reject(rows: list[list[str]], tmp_path) -> None:
    csv_path, schema_path = _write_fixture(tmp_path, rows)
    with pytest.raises(ContractError) as excinfo:
        inspect_sidecar(csv_path, schema_path, scratch_dir=tmp_path)
    assert excinfo.value.code == "SOURCE_DATA_INVALID"


def test_schema_rejects_storage_mismatch_and_noncontiguous_ids(tmp_path) -> None:
    csv_path, schema_path = _write_fixture(tmp_path)
    schema = _schema()
    schema["columns"][0]["storage_type"] = "number"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    with pytest.raises(ContractError) as excinfo:
        inspect_sidecar(csv_path, schema_path, scratch_dir=tmp_path)
    assert excinfo.value.code == "SOURCE_SCHEMA_INVALID"
