"""Build job result documents with an `ok` field computed by this code.

`ok` is deliberately not a parameter of build_result: it is derived from
`steps` and `invariants` on every call, so nothing upstream -- a job
manifest, a caller, a partially-trusted adapter -- can set it independently
of whether the job actually succeeded.
"""

from __future__ import annotations

from .schemas import SUPPORTED_SCHEMA_VERSION, validate_result


def compute_ok(steps: list, invariants: list) -> bool:
    """True iff every step succeeded and every declared invariant passed."""
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
    """Compose a result document. Raises ContractError if it fails schema validation.

    Always validates against the result schema before returning -- there is no
    way to opt out, and the schema version is always the one this control
    plane implements. Skipping validation or varying the schema version would
    defeat this module's entire purpose: guaranteeing `ok` (and the rest of
    the document) can never be independently/incorrectly set.
    """
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
