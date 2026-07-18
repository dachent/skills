"""Simulate the state-machine path a job's steps would take, with no Excel.

`cli.py dry-run` uses this to prove a manifest's structural shape maps to a
legal, deterministic sequence of states, before any execution code (#36)
exists to actually run it.
"""

from __future__ import annotations

from .errors import ContractError
from .schemas import KNOWN_STEP_TYPES
from .state_machine import transition

_PREAMBLE = ("QUEUED", "STAGING_INPUT", "INSPECTING_WORKBOOK", "SELECTING_BACKENDS", "STARTING_EXCEL")

# Every job validates before saving, saves, reopens the saved output to
# revalidate it, then publishes -- regardless of which steps it declared.
# "success" is impossible without walking through this tail (RFC 0001,
# "Workbook validation contracts": a successful COM call is never sufficient
# evidence of success on its own).
_POSTAMBLE = ("VALIDATING", "SAVING", "REOPEN_VALIDATION", "PUBLISHING", "SUCCEEDED")

# Step types whose state sequence doesn't depend on the step's own fields.
# "refresh" is handled separately below because its sequence depends on
# `connections`; "save_as" maps to no distinct mid-sequence state because
# SAVING is already guaranteed by the fixed postamble every job walks
# through.
_FIXED_STEP_STATES = {
    "open": ("OPENING_WORKBOOK",),
    "recalc": ("CALCULATING",),
    "run_approved_macro": ("RUNNING_APPROVED_MACRO",),
    "save_as": (),
}

# One Python-side source of truth for "which step types exist": this asserts
# that _FIXED_STEP_STATES + the separately-handled "refresh" cover exactly
# the step types schemas.py (and, transitively, job.schema.json) knows about,
# so adding a 6th step type without updating this module fails loudly here
# instead of silently mis-mapping it.
assert _FIXED_STEP_STATES.keys() | {"refresh"} == KNOWN_STEP_TYPES


def _states_for_step(step: dict) -> tuple:
    step_type = step.get("type")

    if step_type == "refresh":
        if step.get("connections") == "all":
            return ("REFRESHING_CONNECTIONS", "REFRESHING_DATA_MODEL", "REFRESHING_PIVOTS")
        return ("REFRESHING_CONNECTIONS",)

    if step_type in _FIXED_STEP_STATES:
        return _FIXED_STEP_STATES[step_type]

    raise ContractError(
        "UNKNOWN_STEP_TYPE",
        f"Unknown step type {step_type!r}; cannot map it to a state.",
        {"type": step_type},
    )


def _collapse_adjacent_duplicates(states: list) -> list:
    collapsed: list = []
    for state in states:
        if not collapsed or collapsed[-1] != state:
            collapsed.append(state)
    return collapsed


def _assert_legal_sequence(states: list) -> None:
    for earlier, later in zip(states, states[1:]):
        transition(earlier, later)


def simulate_transitions(job: dict, *, cancel_after_state: str | None = None) -> list:
    """Return the ordered list of states this job's steps would traverse.

    Deterministic: the same job always maps to the same sequence, so
    re-submitting a job under the same idempotency_key is safe to reason
    about at this layer.

    If `cancel_after_state` names a state that occurs in the sequence, the
    sequence is truncated right after it and CANCELLED is appended,
    simulating a cancellation delivered mid-job. Raises ContractError if the
    job's steps don't map to a legal sequence, or if the requested
    cancellation point never occurs in it.
    """
    states = list(_PREAMBLE)
    for step in job["steps"]:
        states.extend(_states_for_step(step))
    states.extend(_POSTAMBLE)
    states = _collapse_adjacent_duplicates(states)

    if cancel_after_state is not None:
        if cancel_after_state not in states:
            raise ContractError(
                "STATE_TRANSITION_INVALID",
                f"Cannot cancel after {cancel_after_state!r}: it does not occur in "
                "this job's state sequence.",
                {"cancel_after_state": cancel_after_state, "sequence": states},
            )
        cut = states.index(cancel_after_state) + 1
        states = states[:cut] + ["CANCELLED"]

    _assert_legal_sequence(states)
    return states
