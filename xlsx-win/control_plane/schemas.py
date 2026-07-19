"""Load and validate the versioned xlsx-win JSON contracts."""

from __future__ import annotations

import json
import ntpath
from pathlib import Path

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for

from .errors import ContractError

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
LEGACY_SCHEMA_VERSION = "2.0"
COMPOSITE_SCHEMA_VERSION = "2.1"
SUPPORTED_SCHEMA_VERSION = LEGACY_SCHEMA_VERSION
SUPPORTED_SCHEMA_VERSIONS = frozenset({LEGACY_SCHEMA_VERSION, COMPOSITE_SCHEMA_VERSION})
LEGACY_STEP_TYPES = frozenset({"open", "refresh", "recalc", "run_approved_macro", "save_as"})
COMPOSITE_STEP_TYPES = frozenset({"append_table_rows", "replace_table_data"})
# Compatibility alias used by the legacy dry-run and v2.0 schema tests.
KNOWN_STEP_TYPES = LEGACY_STEP_TYPES
ALL_STEP_TYPES = LEGACY_STEP_TYPES | COMPOSITE_STEP_TYPES


def _load_schema(file_name: str) -> dict:
    return json.loads((SCHEMA_DIR / file_name).read_text(encoding="utf-8"))


JOB_SCHEMA = _load_schema("job.schema.json")
RESULT_SCHEMA = _load_schema("result.schema.json")
JOB_SCHEMA_V21 = _load_schema("job-v2.1.schema.json")
RESULT_SCHEMA_V21 = _load_schema("result-v2.1.schema.json")
VALIDATION_CONTRACT_SCHEMA = _load_schema("validation_contract.schema.json")
AUDIT_MANIFEST_SCHEMA = _load_schema("audit_manifest.schema.json")

_JOB_VALIDATOR = validator_for(JOB_SCHEMA)(JOB_SCHEMA)
_RESULT_VALIDATOR = validator_for(RESULT_SCHEMA)(RESULT_SCHEMA)
_JOB_VALIDATOR_V21 = validator_for(JOB_SCHEMA_V21)(JOB_SCHEMA_V21)
_RESULT_VALIDATOR_V21 = validator_for(RESULT_SCHEMA_V21)(RESULT_SCHEMA_V21)
_CONTRACT_VALIDATOR = validator_for(VALIDATION_CONTRACT_SCHEMA)(VALIDATION_CONTRACT_SCHEMA)
_AUDIT_MANIFEST_VALIDATOR = validator_for(AUDIT_MANIFEST_SCHEMA)(AUDIT_MANIFEST_SCHEMA)

_JOB_VALIDATORS = {
    LEGACY_SCHEMA_VERSION: _JOB_VALIDATOR,
    COMPOSITE_SCHEMA_VERSION: _JOB_VALIDATOR_V21,
}
_RESULT_VALIDATORS = {
    LEGACY_SCHEMA_VERSION: _RESULT_VALIDATOR,
    COMPOSITE_SCHEMA_VERSION: _RESULT_VALIDATOR_V21,
}


def _known_step_type_violation(instance) -> ContractError | None:
    steps = instance.get("steps") if isinstance(instance, dict) else None
    if not isinstance(steps, list):
        return None

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if step_type is not None and step_type not in ALL_STEP_TYPES:
            return ContractError(
                "UNKNOWN_STEP_TYPE",
                f"Unknown step type {step_type!r} at steps[{index}].",
                {"step_index": index, "type": step_type},
            )
    return None


def _version_mismatch_violation(instance) -> ContractError | None:
    if not isinstance(instance, dict):
        return None

    version = instance.get("schema_version")
    if version is not None and version not in SUPPORTED_SCHEMA_VERSIONS:
        return ContractError(
            "MANIFEST_VERSION_MISMATCH",
            f"Unsupported schema_version {version!r}; this control plane implements "
            f"{sorted(SUPPORTED_SCHEMA_VERSIONS)!r}.",
            {
                "received": version,
                "expected": LEGACY_SCHEMA_VERSION,
                "supported": sorted(SUPPORTED_SCHEMA_VERSIONS),
            },
        )
    return None


def _classify_job_error(instance, exc: ValidationError) -> ContractError:
    for check in (_version_mismatch_violation, _known_step_type_violation):
        violation = check(instance)
        if violation is not None:
            return violation

    return ContractError(
        "SCHEMA_INVALID",
        exc.message,
        {"json_path": list(exc.absolute_path), "validator": exc.validator},
    )


def _writable_run_count(columns: list[dict]) -> int:
    count = 0
    in_writable_run = False
    for column in columns:
        is_writable = column.get("role") == "writable"
        if is_writable and not in_writable_run:
            count += 1
        in_writable_run = is_writable
    return count


def _raise_semantic(message: str, details: dict) -> None:
    raise ContractError("COMPOSITE_SEMANTICS_INVALID", message, details)


def _validate_composite_semantics(instance: dict) -> None:
    operation = instance["steps"][0]
    table = operation["table"]
    source = operation["source"]
    columns = table["columns"]

    observed_counts = {
        "table.column_count": table["column_count"],
        "len(table.columns)": len(columns),
        "source.column_count": source["column_count"],
        "len(source.cardinality)": len(source["cardinality"]),
    }
    if len(set(observed_counts.values())) != 1:
        _raise_semantic("Composite column counts disagree.", observed_counts)

    declared_runs = {
        "computed": _writable_run_count(columns),
        "table.writable_runs": table["writable_runs"],
        "source.writable_runs": source["writable_runs"],
    }
    if len(set(declared_runs.values())) != 1:
        _raise_semantic("Composite writable-run counts disagree.", declared_runs)

    existing_rows = table["existing_body_rows"]
    source_rows = source["row_count"]
    final_rows = table["final_body_rows"]
    if operation["type"] == "append_table_rows":
        expected_final_rows = existing_rows + source_rows
    else:
        expected_final_rows = source_rows
        if table.get("saved_sort") is not None:
            _raise_semantic(
                "The initial replacement profile does not support a saved sort descriptor.",
                {"operation": operation["type"], "saved_sort": table["saved_sort"]},
            )
    if final_rows != expected_final_rows:
        _raise_semantic(
            "Composite row arithmetic is invalid.",
            {
                "operation": operation["type"],
                "existing_body_rows": existing_rows,
                "source_rows": source_rows,
                "declared_final_rows": final_rows,
                "expected_final_rows": expected_final_rows,
            },
        )

    input_path = ntpath.normcase(ntpath.abspath(operation["workbook_path"]))
    output_path = ntpath.normcase(ntpath.abspath(operation["output_path"]))
    if input_path == output_path:
        _raise_semantic(
            "Composite output_path must differ from workbook_path; seeds are immutable.",
            {"workbook_path": operation["workbook_path"], "output_path": operation["output_path"]},
        )

    timeouts = instance["timeouts"]
    phase_names = (
        "preflight_seconds",
        "write_seconds",
        "calculation_seconds",
        "pivot_seconds",
        "save_seconds",
        "reopen_seconds",
        "validation_seconds",
        "close_seconds",
    )
    largest_phase = max(timeouts[name] for name in phase_names)
    if timeouts["whole_job_seconds"] < largest_phase:
        _raise_semantic(
            "whole_job_seconds cannot be shorter than an individual phase deadline.",
            {"whole_job_seconds": timeouts["whole_job_seconds"], "largest_phase": largest_phase},
        )


def validate_job(instance: dict) -> None:
    """Validate a job manifest without touching Excel or caller files."""
    version_violation = _version_mismatch_violation(instance)
    if version_violation is not None:
        raise version_violation

    version = instance.get("schema_version") if isinstance(instance, dict) else None
    validator = _JOB_VALIDATORS.get(version, _JOB_VALIDATOR)
    try:
        validator.validate(instance)
    except ValidationError as exc:
        raise _classify_job_error(instance, exc) from exc

    if version == COMPOSITE_SCHEMA_VERSION:
        _validate_composite_semantics(instance)


def validate_result(instance: dict) -> None:
    """Validate a computed result document against its versioned result schema."""
    version = instance.get("schema_version") if isinstance(instance, dict) else None
    if version not in SUPPORTED_SCHEMA_VERSIONS:
        raise ContractError(
            "RESULT_VERSION_MISMATCH",
            f"Unsupported result schema_version {version!r}.",
            {"received": version, "expected": sorted(SUPPORTED_SCHEMA_VERSIONS)},
        )
    try:
        _RESULT_VALIDATORS[version].validate(instance)
    except ValidationError as exc:
        raise ContractError(
            "SCHEMA_INVALID",
            exc.message,
            {"json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc


def validate_contract(instance: dict) -> None:
    """Validate a workbook validation-contract sidecar."""
    try:
        _CONTRACT_VALIDATOR.validate(instance)
    except ValidationError as exc:
        raise ContractError(
            "SCHEMA_INVALID",
            exc.message,
            {"json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc


def validate_audit_manifest(instance: dict) -> None:
    """Validate a computed audit manifest document."""
    try:
        _AUDIT_MANIFEST_VALIDATOR.validate(instance)
    except ValidationError as exc:
        raise ContractError(
            "SCHEMA_INVALID",
            exc.message,
            {"json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc
