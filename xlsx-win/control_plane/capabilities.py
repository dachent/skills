"""Immutable capability profiles and fail-closed composite admission."""

from __future__ import annotations

import hashlib
import json
import ntpath
from pathlib import Path

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for

from .errors import ContractError
from .schemas import COMPOSITE_SCHEMA_VERSION, SCHEMA_DIR, validate_job

CAPABILITY_DIR = Path(__file__).resolve().parent.parent / "capabilities"
CAPABILITY_SCHEMA = json.loads((SCHEMA_DIR / "capability-profile.schema.json").read_text(encoding="utf-8"))
_CAPABILITY_VALIDATOR = validator_for(CAPABILITY_SCHEMA)(CAPABILITY_SCHEMA)


def _canonical_bytes(profile: dict) -> bytes:
    return json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def profile_sha256(profile: dict) -> str:
    return hashlib.sha256(_canonical_bytes(profile)).hexdigest()


def validate_profile(profile: dict) -> None:
    try:
        _CAPABILITY_VALIDATOR.validate(profile)
    except ValidationError as exc:
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            exc.message,
            {"json_path": list(exc.absolute_path), "validator": exc.validator},
        ) from exc

    for name, bounds in profile["limits"].items():
        if isinstance(bounds, dict) and bounds["min"] > bounds["max"]:
            raise ContractError(
                "CAPABILITY_PROFILE_INVALID",
                f"Capability limit {name!r} has min greater than max.",
                {"limit": name, "min": bounds["min"], "max": bounds["max"]},
            )
    qualification = profile["qualification"]
    if profile["status"] in {"beta", "certified"} and (
        qualification["completed_clean_jobs"] < qualification["minimum_complete_jobs"]
        or not qualification["mandatory_fault_points_complete"]
        or not qualification["exact_fixture_complete"]
    ):
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            "A beta or certified profile must contain complete qualification evidence.",
            {"profile": profile["id"], "qualification": qualification},
        )


def load_profiles() -> dict[str, dict]:
    profiles: dict[str, dict] = {}
    for path in sorted(CAPABILITY_DIR.glob("*.json")):
        profile = json.loads(path.read_text(encoding="utf-8"))
        validate_profile(profile)
        if profile["id"] in profiles:
            raise ContractError(
                "CAPABILITY_PROFILE_INVALID",
                f"Duplicate capability profile id {profile['id']!r}.",
                {"path": str(path)},
            )
        profiles[profile["id"]] = profile
    return profiles


def capability_inventory() -> list[dict]:
    return [
        {
            "id": profile["id"],
            "status": profile["status"],
            "operation": profile["operation"],
            "candidate": profile["candidate"],
            "sha256": profile_sha256(profile),
            "qualification": profile["qualification"],
        }
        for profile in load_profiles().values()
    ]


def _within(name: str, actual: int, bounds: dict, failures: list[dict]) -> None:
    if actual < bounds["min"] or actual > bounds["max"]:
        failures.append({"limit": name, "actual": actual, "allowed": bounds})


def admit_manifest(
    manifest: dict,
    *,
    environment: dict | None = None,
    required_status: str | None = None,
) -> dict:
    """Return the bound profile or reject before mutation.

    Environment keys, when supplied, are ``windows_build``, ``excel_build``,
    ``office_bitness``, ``dotnet_runtime``, ``locale``, and ``date_system``.
    Omitting environment is useful for offline contract validation; a runtime
    must supply it before opening Excel.
    """
    validate_job(manifest)
    if manifest.get("schema_version") != COMPOSITE_SCHEMA_VERSION:
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            "Capability admission applies only to composite schema 2.1.",
            {"schema_version": manifest.get("schema_version")},
        )
    operation = manifest["steps"][0]
    profile_id = operation["capability_profile"]
    profiles = load_profiles()
    if profile_id not in profiles:
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            f"Unknown capability profile {profile_id!r}.",
            {"profile": profile_id, "known_profiles": sorted(profiles)},
        )
    profile = profiles[profile_id]
    failures: list[dict] = []

    if profile["operation"] != operation["type"]:
        failures.append({"check": "operation", "actual": operation["type"], "allowed": profile["operation"]})
    if required_status is not None and profile["status"] != required_status:
        failures.append({"check": "status", "actual": profile["status"], "required": required_status})
    if ntpath.splitext(operation["workbook_path"])[1].lower() != profile["features"]["extension"]:
        failures.append({"check": "extension", "actual": ntpath.splitext(operation["workbook_path"])[1].lower()})

    source = operation["source"]
    table = operation["table"]
    pivots = operation["dependent_pivots"]
    limits = profile["limits"]
    _within("source_rows", source["row_count"], limits["source_rows"], failures)
    _within("final_rows", table["final_body_rows"], limits["final_rows"], failures)
    _within("columns", source["column_count"], limits["columns"], failures)
    _within("total_cells", table["final_body_rows"] * source["column_count"], limits["total_cells"], failures)
    _within("encoded_bytes", source["encoded_bytes"], limits["encoded_bytes"], failures)
    _within("text_bytes", source["text_bytes"], limits["text_bytes"], failures)
    _within("max_cardinality", max(source["cardinality"], default=0), limits["max_cardinality"], failures)
    _within("writable_runs", source["writable_runs"], limits["writable_runs"], failures)
    _within("pivot_caches", pivots["cache_count"], limits["pivot_caches"], failures)
    _within("pivot_reports", pivots["report_count"], limits["pivot_reports"], failures)

    saved_sort_policy = profile["features"]["saved_sort"]
    if saved_sort_policy == "required_descriptor" and not isinstance(table.get("saved_sort"), dict):
        failures.append({"check": "saved_sort", "required": "descriptor"})
    if saved_sort_policy == "absent" and table.get("saved_sort") is not None:
        failures.append({"check": "saved_sort", "required": "absent"})
    if pivots["profile"] != profile["features"]["pivot_profile"]:
        failures.append({"check": "pivot_profile", "actual": pivots["profile"]})

    if environment is not None:
        env = profile["environment"]
        membership = {
            "windows_build": "windows_builds",
            "excel_build": "excel_builds",
            "locale": "locales",
            "date_system": "date_systems",
        }
        for actual_name, allowed_name in membership.items():
            if environment.get(actual_name) not in env[allowed_name]:
                failures.append(
                    {"check": actual_name, "actual": environment.get(actual_name), "allowed": env[allowed_name]}
                )
        for exact in ("office_bitness", "dotnet_runtime"):
            if environment.get(exact) != env[exact]:
                failures.append({"check": exact, "actual": environment.get(exact), "allowed": env[exact]})

    if failures:
        raise ContractError(
            "CAPABILITY_PROFILE_INVALID",
            "Manifest is outside the declared capability profile.",
            {"profile": profile_id, "failures": failures},
        )
    return {"profile": profile, "sha256": profile_sha256(profile)}
