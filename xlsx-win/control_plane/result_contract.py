"""Build and verify versioned xlsx-win result documents.

The v2.0 result contract is retained for compatibility.  The v2.1 composite
contract is intentionally stricter: success requires one exact, versioned proof
set, complete cleanup, and atomic publication of the bytes that were verified.
No producer-supplied ``ok`` value is trusted.
"""

from __future__ import annotations

from collections import Counter

from .errors import ContractError
from .schemas import COMPOSITE_SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSION, validate_result


COMMON_COMPOSITE_INVARIANTS = frozenset(
    {
        "seed_immutable",
        "source_hash_bound",
        "schema_hash_bound",
        "plan_hash_bound",
        "table_identity_preserved",
        "table_geometry_exact",
        "header_schema_exact",
        "body_typed_hash_exact",
        "calculated_columns_exact",
        "formula_state_exact",
        "filter_sort_state_exact",
        "pivot_topology_exact",
        "pivot_cache_source_exact",
        "pivot_reports_exact",
        "fresh_reopen_exact",
        "non_allowlisted_parts_unchanged",
    }
)

OPERATION_INVARIANTS = {
    "append_table_rows": COMMON_COMPOSITE_INVARIANTS
    | frozenset({"existing_prefix_preserved", "appended_rows_exact", "saved_sort_descriptor_preserved"}),
    "replace_table_data": COMMON_COMPOSITE_INVARIANTS
    | frozenset({"replacement_rows_exact", "old_tail_absent"}),
}

REQUIRED_BINDINGS = frozenset(
    {"workbook", "source", "schema", "plan", "staged_output", "verifier", "evidence"}
)
REQUIRED_CLEANUP = frozenset(
    {"owned_processes_zero", "worker_exit_verified", "excel_exit_verified", "termination_verified"}
)


def compute_ok(steps: list, invariants: list) -> bool:
    """Legacy v2.0 result computation."""
    if any(step.get("status") != "succeeded" for step in steps):
        return False
    if any(not invariant.get("passed", False) for invariant in invariants):
        return False
    return True


def build_result(
    *,
    run_id: str,
    idempotency_key: str,
    final_state: str,
    steps: list,
    invariants: list | None = None,
) -> dict:
    """Compose and validate a legacy v2.0 result document."""
    invariants = invariants if invariants is not None else []
    result = {
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "run_id": run_id,
        "idempotency_key": idempotency_key,
        "final_state": final_state,
        "steps": steps,
        "invariants": invariants,
        "ok": compute_ok(steps, invariants),
    }
    validate_result(result)
    return result


def required_composite_invariants(operation: str) -> frozenset[str]:
    """Return the only accepted proof registry for a composite operation."""
    try:
        return OPERATION_INVARIANTS[operation]
    except KeyError as exc:
        raise ContractError(
            "RESULT_PROOF_INVALID",
            f"No invariant registry exists for operation {operation!r}.",
            {"operation": operation, "known_operations": sorted(OPERATION_INVARIANTS)},
        ) from exc


def _proof_failures(result: dict, *, require_publication: bool) -> list[dict]:
    failures: list[dict] = []
    operation = result.get("operation")
    required = required_composite_invariants(operation)
    invariants = result.get("invariants") if isinstance(result.get("invariants"), list) else []
    names = [item.get("name") for item in invariants if isinstance(item, dict)]
    counts = Counter(names)
    actual = set(names)

    missing = sorted(required - actual)
    unexpected = sorted(actual - required)
    duplicates = sorted(name for name, count in counts.items() if count != 1)
    if missing or unexpected or duplicates or len(invariants) != len(required):
        failures.append(
            {
                "check": "exact_invariant_registry",
                "missing": missing,
                "unexpected": unexpected,
                "duplicates": duplicates,
                "expected_count": len(required),
                "actual_count": len(invariants),
            }
        )

    bad_invariants = sorted(
        item.get("name", "<unnamed>")
        for item in invariants
        if not isinstance(item, dict)
        or item.get("version") != "1.0"
        or item.get("passed") is not True
        or not isinstance(item.get("evidence_sha256"), str)
        or len(item.get("evidence_sha256", "")) != 64
    )
    if bad_invariants:
        failures.append({"check": "all_invariants_passed_and_evidenced", "failed": bad_invariants})

    if result.get("final_state") != "SUCCEEDED":
        failures.append({"check": "terminal_state", "actual": result.get("final_state")})

    steps = result.get("steps") if isinstance(result.get("steps"), list) else []
    if not steps or any(step.get("status") != "succeeded" for step in steps if isinstance(step, dict)):
        failures.append({"check": "all_steps_succeeded"})

    bindings = result.get("bindings") if isinstance(result.get("bindings"), dict) else {}
    if set(bindings) != REQUIRED_BINDINGS or any(
        not isinstance(value, str) or len(value) != 64 for value in bindings.values()
    ):
        failures.append({"check": "exact_bindings", "actual": sorted(bindings)})

    cleanup = result.get("cleanup") if isinstance(result.get("cleanup"), dict) else {}
    if set(cleanup) != REQUIRED_CLEANUP or any(cleanup.get(name) is not True for name in REQUIRED_CLEANUP):
        failures.append({"check": "cleanup_complete", "actual": cleanup})

    profile = result.get("profile") if isinstance(result.get("profile"), dict) else {}
    if not profile.get("id") or len(profile.get("sha256", "")) != 64 or len(profile.get("build_commit", "")) != 40:
        failures.append({"check": "profile_bound", "actual": profile})

    publication = result.get("publication") if isinstance(result.get("publication"), dict) else {}
    staged_hash = publication.get("staged_sha256")
    destination_hash = publication.get("destination_sha256")
    if staged_hash != bindings.get("staged_output"):
        failures.append({"check": "publication_staged_binding"})
    if require_publication or publication.get("status") == "published":
        if (
            publication.get("status") != "published"
            or publication.get("atomic") is not True
            or staged_hash != destination_hash
        ):
            failures.append({"check": "atomic_publication", "actual": publication})
    elif publication.get("status") not in {"not_attempted", "published"}:
        failures.append({"check": "publication_state", "actual": publication.get("status")})

    return failures


def publication_eligible(result: dict) -> bool:
    """True only when every pre-publication proof and cleanup gate is complete."""
    try:
        validate_result(result)
        return not _proof_failures(result, require_publication=False)
    except ContractError:
        return False


def compute_composite_ok(result: dict) -> bool:
    """Recompute composite success, including exact atomic publication proof."""
    try:
        return not _proof_failures(result, require_publication=True)
    except ContractError:
        return False


def validate_composite_result(result: dict) -> None:
    """Validate schema and reject a producer-supplied or incomplete success proof."""
    validate_result(result)
    if result.get("schema_version") != COMPOSITE_SCHEMA_VERSION:
        raise ContractError(
            "RESULT_VERSION_MISMATCH",
            "Composite proof validation requires result schema 2.1.",
            {"received": result.get("schema_version"), "expected": COMPOSITE_SCHEMA_VERSION},
        )
    failures = _proof_failures(result, require_publication=result.get("ok") is True)
    recomputed = not _proof_failures(result, require_publication=True)
    if result.get("ok") is not recomputed:
        failures.append(
            {"check": "computed_ok", "producer_value": result.get("ok"), "computed_value": recomputed}
        )
    if failures:
        raise ContractError(
            "RESULT_PROOF_INVALID",
            "Composite result proof is incomplete or internally inconsistent.",
            {"failures": failures},
        )


def build_composite_result(
    *,
    run_id: str,
    idempotency_key: str,
    operation: str,
    final_state: str,
    steps: list,
    invariants: list,
    bindings: dict,
    profile: dict,
    cleanup: dict,
    publication: dict,
) -> dict:
    """Compose a v2.1 result with ``ok`` derived from the complete proof."""
    result = {
        "schema_version": COMPOSITE_SCHEMA_VERSION,
        "run_id": run_id,
        "idempotency_key": idempotency_key,
        "operation": operation,
        "operation_version": "1.0",
        "final_state": final_state,
        "steps": steps,
        "invariants": invariants,
        "bindings": bindings,
        "profile": profile,
        "cleanup": cleanup,
        "publication": publication,
        "ok": False,
    }
    validate_result(result)
    result["ok"] = compute_composite_ok(result)
    validate_result(result)
    return result
