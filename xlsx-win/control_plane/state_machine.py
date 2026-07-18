"""Job state machine: the enumerated states, legal transitions, and terminal check.

Contract-only: nothing here drives Excel. This describes the progress a job's
steps would move through if executed by the runtime built in #36.
"""

from __future__ import annotations

from .errors import ContractError

STATES = (
    "QUEUED",
    "STAGING_INPUT",
    "INSPECTING_WORKBOOK",
    "SELECTING_BACKENDS",
    "STARTING_EXCEL",
    "OPENING_WORKBOOK",
    "APPLYING_EDITS",
    "UPDATING_LINKS",
    "REFRESHING_CONNECTIONS",
    "REFRESHING_DATA_MODEL",
    "REFRESHING_PIVOTS",
    "CALCULATING",
    "RUNNING_APPROVED_MACRO",
    "VALIDATING",
    "SAVING",
    "REOPEN_VALIDATION",
    "PUBLISHING",
    "SUCCEEDED",
    "FAILED",
    "TIMED_OUT",
    "CANCELLED",
)

TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"})

# The three ways a job can end early. Reachable from any non-terminal state.
_ABORT_STATES = frozenset({"FAILED", "TIMED_OUT", "CANCELLED"})

# Non-abort states grouped into forward-only phases. A job may never return to
# an earlier phase, but within the "compute" phase, edits/link-updates/refresh
# (connections, data model, pivots)/calculation/approved-macro steps may
# interleave and repeat in any order and count -- a job legitimately recalcs,
# runs a macro, then recalcs again, all sharing one Excel lifecycle.
_PHASES = (
    frozenset({"QUEUED"}),
    frozenset({"STAGING_INPUT"}),
    frozenset({"INSPECTING_WORKBOOK"}),
    frozenset({"SELECTING_BACKENDS"}),
    frozenset({"STARTING_EXCEL"}),
    frozenset({"OPENING_WORKBOOK"}),
    frozenset(
        {
            "APPLYING_EDITS",
            "UPDATING_LINKS",
            "REFRESHING_CONNECTIONS",
            "REFRESHING_DATA_MODEL",
            "REFRESHING_PIVOTS",
            "CALCULATING",
            "RUNNING_APPROVED_MACRO",
        }
    ),
    frozenset({"VALIDATING"}),
    frozenset({"SAVING"}),
    frozenset({"REOPEN_VALIDATION"}),
    frozenset({"PUBLISHING"}),
    frozenset({"SUCCEEDED"}),
)


def _phase_index(state: str) -> int:
    for index, phase in enumerate(_PHASES):
        if state in phase:
            return index
    raise ValueError(f"State {state!r} has no phase (is it an abort state?).")


def is_terminal(state: str) -> bool:
    if state not in STATES:
        raise ValueError(f"Unknown state: {state!r}")
    return state in TERMINAL_STATES


def can_transition(from_state: str, to_state: str) -> bool:
    if from_state not in STATES:
        raise ValueError(f"Unknown state: {from_state!r}")
    if to_state not in STATES:
        raise ValueError(f"Unknown state: {to_state!r}")

    if from_state == to_state:
        return False

    if is_terminal(from_state):
        return False

    if to_state in _ABORT_STATES:
        return True

    return _phase_index(to_state) >= _phase_index(from_state)


def transition(from_state: str, to_state: str) -> str:
    """Return to_state if the transition is legal, else raise ContractError."""
    if not can_transition(from_state, to_state):
        raise ContractError(
            "STATE_TRANSITION_INVALID",
            f"Illegal state transition: {from_state} -> {to_state}.",
            {"from_state": from_state, "to_state": to_state},
        )
    return to_state
