"""State machine tests: legal transitions and terminal-state detection.

The state list is fixed by the amendment ("reuse this exact list, it's
already decided") -- these tests pin that list and the transition rules
around it.
"""

from __future__ import annotations

import pytest

from control_plane.errors import ContractError
from control_plane.state_machine import STATES, TERMINAL_STATES, can_transition, is_terminal, transition

EXPECTED_STATES = (
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


def test_states_match_the_decided_list_exactly() -> None:
    assert STATES == EXPECTED_STATES


def test_terminal_states_are_exactly_the_four_final_statuses() -> None:
    assert TERMINAL_STATES == {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED"}
    for state in STATES:
        assert is_terminal(state) == (state in TERMINAL_STATES)


def test_is_terminal_rejects_unknown_state() -> None:
    with pytest.raises(ValueError):
        is_terminal("NOT_A_STATE")


def test_forward_progression_is_legal() -> None:
    assert can_transition("QUEUED", "STAGING_INPUT")
    assert can_transition("STAGING_INPUT", "OPENING_WORKBOOK")  # skipping stages is allowed
    assert can_transition("SAVING", "PUBLISHING")
    assert can_transition("PUBLISHING", "SUCCEEDED")


def test_backward_progression_is_illegal() -> None:
    assert not can_transition("SAVING", "STAGING_INPUT")
    assert not can_transition("CALCULATING", "OPENING_WORKBOOK")


def test_self_transition_is_illegal() -> None:
    assert not can_transition("CALCULATING", "CALCULATING")


def test_any_non_terminal_state_can_abort_to_a_terminal_state() -> None:
    for abort_state in ("FAILED", "TIMED_OUT", "CANCELLED"):
        assert can_transition("QUEUED", abort_state)
        assert can_transition("REFRESHING_CONNECTIONS", abort_state)
        assert can_transition("PUBLISHING", abort_state)


def test_terminal_states_have_no_outgoing_transitions() -> None:
    for terminal_state in TERMINAL_STATES:
        for other_state in STATES:
            assert not can_transition(terminal_state, other_state)


def test_can_transition_rejects_unknown_states() -> None:
    with pytest.raises(ValueError):
        can_transition("NOT_A_STATE", "QUEUED")
    with pytest.raises(ValueError):
        can_transition("QUEUED", "NOT_A_STATE")


def test_transition_returns_target_state_when_legal() -> None:
    assert transition("QUEUED", "STAGING_INPUT") == "STAGING_INPUT"


def test_transition_raises_contract_error_when_illegal() -> None:
    with pytest.raises(ContractError) as excinfo:
        transition("SAVING", "STAGING_INPUT")

    assert excinfo.value.code == "STATE_TRANSITION_INVALID"
    assert excinfo.value.details == {"from_state": "SAVING", "to_state": "STAGING_INPUT"}
