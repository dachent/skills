"""Load the xlsx-win v2 JSON Schemas and validate manifests/results against them.

Validation never touches Excel, openpyxl, or the filesystem outside this
package's own schemas/ directory. Structural error formatting is left to
jsonschema's own ValidationError -- this module only classifies *which*
normalized error code a failure maps to.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for

from .errors import ContractError

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
SUPPORTED_SCHEMA_VERSION = "2.0"
KNOWN_STEP_TYPES = frozenset({"open", "refresh", "recalc", "run_approved_macro", "save_as"})


def _load_schema(file_name: str) -> dict:
    return json.loads((SCHEMA_DIR / file_name).read_text(encoding="utf-8"))


JOB_SCHEMA = _load_schema("job.schema.json")
RESULT_SCHEMA = _load_schema("result.schema.json")

_JOB_VALIDATOR = validator_for(JOB_SCHEMA)(JOB_SCHEMA)
_RESULT_VALIDATOR = validator_for(RESULT_SCHEMA)(RESULT_SCHEMA)


def _known_step_type_violation(instance) -> ContractError | None:
    steps = instance.get("steps") if isinstance(instance, dict) else None
    if not isinstance(steps, list):
        return None

    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        step_type = step.get("type")
        if step_type is not None and step_type not in KNOWN_STEP_TYPES:
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
    if version is not None and version != SUPPORTED_SCHEMA_VERSION:
        return ContractError(
            "MANIFEST_VERSION_MISMATCH",
            f"Unsupported schema_version {version!r}; this control plane implements "
            f"{SUPPORTED_SCHEMA_VERSION!r}.",
            {"received": version, "expected": SUPPORTED_SCHEMA_VERSION},
        )
    return None


def _classify_job_error(instance, exc: ValidationError) -> ContractError:
    # More specific codes take priority over the generic SCHEMA_INVALID fallback.
    for check in (_known_step_type_violation, _version_mismatch_violation):
        violation = check(instance)
        if violation is not None:
            return violation

    return ContractError(
        "SCHEMA_INVALID",
        exc.message,
        {"json_path": list(exc.absolute_path), "validator": exc.validator},
    )


def validate_job(instance: dict) -> None:
    """Validate a job manifest against the v2 job schema.

    Raises ContractError on any failure. Never touches Excel.
    """
    try:
        _JOB_VALIDATOR.validate(instance)
    except ValidationError as exc:
        raise _classify_job_error(instance, exc) from exc


def validate_result(instance: dict) -> None:
    """Validate a computed result document against the v2 result schema."""
    try:
        _RESULT_VALIDATOR.validate(instance)
    except ValidationError as exc:
        raise ContractError(
            "SCHEMA_INVALID",
            exc.message,
            {"json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc
