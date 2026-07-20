"""Typed, immutable CSV sidecars for composite Table transactions.

Rows are streamed. Exact cardinality uses a disk-backed SQLite set so memory
does not grow with a 1m-row source. Canonical hashes bind column identity,
logical/storage type, normalized value, date system, and number format.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sqlite3
import tempfile
from contextlib import closing
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterator

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for

from .errors import ContractError
from .schemas import SCHEMA_DIR

SIDECAR_SCHEMA = json.loads((SCHEMA_DIR / "table-sidecar-v1.schema.json").read_text(encoding="utf-8"))
_SIDECAR_VALIDATOR = validator_for(SIDECAR_SCHEMA)(SIDECAR_SCHEMA)

_STORAGE_BY_LOGICAL = {
    "blank": "blank",
    "boolean": "boolean",
    "number": "number",
    "text": "inline_string",
    "datetime": "number",
}


@dataclass(frozen=True)
class TypedCell:
    column_id: int
    name: str
    role: str
    logical_type: str
    storage_type: str
    number_format: str | None
    normalized: str | None
    ooxml_value: str | None


@dataclass(frozen=True)
class SidecarStats:
    raw_sha256: str
    schema_sha256: str
    canonical_sha256: str
    row_count: int
    column_count: int
    encoded_bytes: int
    text_bytes: int
    cardinality: tuple[int, ...]
    writable_runs: int

    def to_dict(self) -> dict:
        return {
            "raw_sha256": self.raw_sha256,
            "schema_sha256": self.schema_sha256,
            "canonical_sha256": self.canonical_sha256,
            "row_count": self.row_count,
            "column_count": self.column_count,
            "encoded_bytes": self.encoded_bytes,
            "text_bytes": self.text_bytes,
            "cardinality": list(self.cardinality),
            "writable_runs": self.writable_runs,
        }


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sidecar_schema(path: str | Path) -> dict:
    schema_path = Path(path)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(
            "SOURCE_SCHEMA_INVALID", f"Cannot read typed sidecar schema: {exc}", {"path": str(schema_path)}
        ) from exc
    try:
        _SIDECAR_VALIDATOR.validate(schema)
    except ValidationError as exc:
        raise ContractError(
            "SOURCE_SCHEMA_INVALID",
            exc.message,
            {"path": str(schema_path), "json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc

    columns = schema["columns"]
    ids = [column["id"] for column in columns]
    names = [column["name"] for column in columns]
    if ids != list(range(1, len(columns) + 1)) or len(set(names)) != len(names):
        raise ContractError(
            "SOURCE_SCHEMA_INVALID",
            "Column ids must be contiguous and one-based; names must be unique.",
            {"ids": ids, "names": names},
        )
    for column in columns:
        expected_storage = _STORAGE_BY_LOGICAL[column["logical_type"]]
        if column["storage_type"] != expected_storage:
            raise ContractError(
                "SOURCE_SCHEMA_INVALID",
                "Logical and storage types disagree.",
                {"column": column["name"], "expected": expected_storage, "actual": column["storage_type"]},
            )
        needs_format = column["logical_type"] == "datetime"
        if needs_format != isinstance(column["number_format"], str):
            raise ContractError(
                "SOURCE_SCHEMA_INVALID",
                "Datetime columns require a number format; all other initial types require null.",
                {"column": column["name"], "logical_type": column["logical_type"]},
            )
    return schema


def _normalize_decimal(raw: str, *, column: dict, row_number: int, datetime_value: bool) -> tuple[str, str]:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise ContractError(
            "SOURCE_DATA_INVALID",
            "Numeric sidecar value is not a finite decimal.",
            {"row": row_number, "column": column["name"], "value": raw},
        ) from exc
    if not value.is_finite():
        raise ContractError(
            "SOURCE_DATA_INVALID",
            "NaN and infinity are not supported.",
            {"row": row_number, "column": column["name"], "value": raw},
        )
    normalized_value = value.normalize()
    significant_digits = len(normalized_value.as_tuple().digits)
    if significant_digits > 15:
        raise ContractError(
            "SOURCE_DATA_INVALID",
            "Numbers exceeding Excel's 15-significant-digit model must be typed as text.",
            {"row": row_number, "column": column["name"], "significant_digits": significant_digits},
        )
    if datetime_value and (value < Decimal("0") or value > Decimal("2958465.999999999")):
        raise ContractError(
            "SOURCE_DATA_INVALID",
            "OA date is outside the supported Excel range.",
            {"row": row_number, "column": column["name"], "value": raw},
        )
    normalized = format(normalized_value, "f")
    if normalized == "-0":
        normalized = "0"
    return normalized, normalized


def _typed_cell(raw: str, column: dict, row_number: int) -> TypedCell:
    logical = column["logical_type"]
    role = column["role"]
    if role == "calculated":
        if raw != "":
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "Calculated-column inputs must be empty; native Excel owns formula fill.",
                {"row": row_number, "column": column["name"]},
            )
        normalized = None
        ooxml_value = None
    elif logical == "blank":
        if raw != "":
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "The only canonical blank representation is an empty CSV field.",
                {"row": row_number, "column": column["name"]},
            )
        normalized = None
        ooxml_value = None
    elif logical == "boolean":
        if raw not in {"TRUE", "FALSE"}:
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "Boolean lexical form must be exactly TRUE or FALSE.",
                {"row": row_number, "column": column["name"], "value": raw},
            )
        normalized = raw.lower()
        ooxml_value = "1" if raw == "TRUE" else "0"
    elif logical in {"number", "datetime"}:
        if raw == "":
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "Writable numeric and datetime values cannot be blank in the initial profile.",
                {"row": row_number, "column": column["name"]},
            )
        normalized, ooxml_value = _normalize_decimal(
            raw, column=column, row_number=row_number, datetime_value=logical == "datetime"
        )
    else:
        if len(raw) > 32767:
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "Excel text exceeds 32,767 characters.",
                {"row": row_number, "column": column["name"], "length": len(raw)},
            )
        normalized = raw
        ooxml_value = raw

    return TypedCell(
        column_id=column["id"],
        name=column["name"],
        role=role,
        logical_type=logical,
        storage_type=column["storage_type"],
        number_format=column["number_format"],
        normalized=normalized,
        ooxml_value=ooxml_value,
    )


def iter_typed_rows(csv_path: str | Path, schema: dict) -> Iterator[list[TypedCell]]:
    path = Path(csv_path)
    try:
        stream = path.open("r", encoding="utf-8", newline="")
    except OSError as exc:
        raise ContractError("SOURCE_DATA_INVALID", f"Cannot open CSV sidecar: {exc}", {"path": str(path)}) from exc
    with stream:
        reader = csv.reader(stream, delimiter=schema["delimiter"], quotechar=schema["quotechar"], strict=True)
        try:
            header = next(reader)
        except (StopIteration, csv.Error) as exc:
            raise ContractError("SOURCE_DATA_INVALID", "CSV sidecar has no readable header.", {"path": str(path)}) from exc
        expected_header = [column["name"] for column in schema["columns"]]
        if header != expected_header:
            raise ContractError(
                "SOURCE_DATA_INVALID",
                "CSV header does not exactly match the typed schema.",
                {"expected": expected_header, "actual": header},
            )
        try:
            for row_number, values in enumerate(reader, start=2):
                if len(values) != len(schema["columns"]):
                    raise ContractError(
                        "SOURCE_DATA_INVALID",
                        "CSV row width does not match the typed schema.",
                        {"row": row_number, "expected": len(schema["columns"]), "actual": len(values)},
                    )
                yield [_typed_cell(value, column, row_number) for value, column in zip(values, schema["columns"])]
        except csv.Error as exc:
            raise ContractError(
                "SOURCE_DATA_INVALID", f"Malformed CSV sidecar: {exc}", {"path": str(path), "line": reader.line_num}
            ) from exc


def _writable_runs(columns: list[dict]) -> int:
    count = 0
    active = False
    for column in columns:
        writable = column["role"] == "writable"
        if writable and not active:
            count += 1
        active = writable
    return count


def inspect_sidecar(csv_path: str | Path, schema_path: str | Path, *, scratch_dir: str | Path | None = None) -> SidecarStats:
    csv_path = Path(csv_path)
    schema_path = Path(schema_path)
    schema = load_sidecar_schema(schema_path)
    canonical = hashlib.sha256()
    row_count = 0
    text_bytes = 0
    created_temp = scratch_dir is None
    db_file = tempfile.NamedTemporaryFile(prefix="xlsx-win-cardinality-", suffix=".sqlite", dir=scratch_dir, delete=False)
    db_path = Path(db_file.name)
    db_file.close()
    try:
        with closing(sqlite3.connect(db_path)) as connection:
            connection.execute("PRAGMA journal_mode=OFF")
            connection.execute("PRAGMA synchronous=OFF")
            connection.execute("CREATE TABLE seen (column_id INTEGER NOT NULL, value BLOB NOT NULL, PRIMARY KEY(column_id, value)) WITHOUT ROWID")
            for row in iter_typed_rows(csv_path, schema):
                row_count += 1
                for cell in row:
                    tuple_bytes = json.dumps(
                        [
                            cell.column_id,
                            cell.name,
                            cell.logical_type,
                            cell.storage_type,
                            cell.normalized,
                            schema["date_system"],
                            cell.number_format,
                        ],
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    canonical.update(len(tuple_bytes).to_bytes(4, "big"))
                    canonical.update(tuple_bytes)
                    if cell.role == "writable" and cell.normalized is not None:
                        connection.execute(
                            "INSERT OR IGNORE INTO seen(column_id, value) VALUES (?, ?)",
                            (cell.column_id, tuple_bytes),
                        )
                        if cell.logical_type == "text":
                            text_bytes += len(cell.normalized.encode("utf-8"))
                if row_count % 10000 == 0:
                    connection.commit()
            connection.commit()
            counts = dict(connection.execute("SELECT column_id, COUNT(*) FROM seen GROUP BY column_id"))
        cardinality = tuple(counts.get(column["id"], 0) for column in schema["columns"])
    finally:
        try:
            db_path.unlink()
        except OSError:
            pass

    if row_count == 0:
        raise ContractError("SOURCE_DATA_INVALID", "CSV sidecar must contain at least one data row.", {"path": str(csv_path)})
    return SidecarStats(
        raw_sha256=_sha256_path(csv_path),
        schema_sha256=_sha256_path(schema_path),
        canonical_sha256=canonical.hexdigest(),
        row_count=row_count,
        column_count=len(schema["columns"]),
        encoded_bytes=csv_path.stat().st_size,
        text_bytes=text_bytes,
        cardinality=cardinality,
        writable_runs=_writable_runs(schema["columns"]),
    )


def verify_source_binding(operation: dict, stats: SidecarStats) -> None:
    source = operation["source"]
    expected = {
        "raw_sha256": source["raw_sha256"].lower(),
        "schema_sha256": source["schema_sha256"].lower(),
        "canonical_sha256": source["canonical_sha256"].lower(),
        "row_count": source["row_count"],
        "column_count": source["column_count"],
        "encoded_bytes": source["encoded_bytes"],
        "text_bytes": source["text_bytes"],
        "cardinality": source["cardinality"],
        "writable_runs": source["writable_runs"],
    }
    actual = stats.to_dict()
    mismatches = {
        name: {"expected": expected[name], "actual": actual[name]}
        for name in expected
        if expected[name] != actual[name]
    }
    if mismatches:
        raise ContractError(
            "SOURCE_BINDING_MISMATCH",
            "Immutable source bytes or recomputed typed statistics do not match the manifest.",
            {"mismatches": mismatches},
        )
