"""Dry-run simulation tests.

Covers the original #34 acceptance criteria "a job whose steps simulate a
cancellation mid-sequence" and "a retry scenario (re-running the same
idempotency key)", at the contract layer. For the retry criterion, two
things are shown separately: the mapping from a manifest to its simulated
state sequence is pure/deterministic (no hidden state), and idempotency_key
specifically is inert to that mapping while `steps` is not. (Whether
re-submitting a job during real execution is deduplicated is an
execution-engine concern for #36, out of scope here.)
"""

from __future__ import annotations

import pytest

from control_plane.dry_run import simulate_transitions
from control_plane.errors import ContractError
from control_plane.state_machine import is_terminal

THREE_STEP_JOB = {
    "schema_version": "2.0",
    "idempotency_key": "retry-me-001",
    "steps": [
        {"type": "open", "workbook_path": "model.xlsx"},
        {"type": "refresh", "connections": "all"},
        {"type": "recalc"},
    ],
}


def test_full_sequence_for_open_refresh_all_recalc() -> None:
    states = simulate_transitions(THREE_STEP_JOB)

    assert states == [
        "QUEUED",
        "STAGING_INPUT",
        "INSPECTING_WORKBOOK",
        "SELECTING_BACKENDS",
        "STARTING_EXCEL",
        "OPENING_WORKBOOK",
        "REFRESHING_CONNECTIONS",
        "REFRESHING_DATA_MODEL",
        "REFRESHING_PIVOTS",
        "CALCULATING",
        "VALIDATING",
        "SAVING",
        "REOPEN_VALIDATION",
        "PUBLISHING",
        "SUCCEEDED",
    ]
    assert is_terminal(states[-1])


def test_refresh_with_named_connections_skips_model_and_pivot_states() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "named-conn-001",
        "steps": [
            {"type": "open", "workbook_path": "model.xlsx"},
            {"type": "refresh", "connections": ["SalesDB"]},
        ],
    }

    states = simulate_transitions(job)

    assert "REFRESHING_CONNECTIONS" in states
    assert "REFRESHING_DATA_MODEL" not in states
    assert "REFRESHING_PIVOTS" not in states


def test_macro_step_maps_to_running_approved_macro() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "macro-001",
        "steps": [{"type": "run_approved_macro", "macro_name": "RefreshDashboard"}],
    }

    states = simulate_transitions(job)

    assert "RUNNING_APPROVED_MACRO" in states


def test_every_job_reaches_saving_and_reopen_validation_before_publishing() -> None:
    # SAVING/REOPEN_VALIDATION are a fixed part of every job's tail (RFC 0001:
    # "no publication unless the validation contract passes"), whether or not
    # the manifest includes an explicit save_as step.
    job_without_save_as = {
        "schema_version": "2.0",
        "idempotency_key": "no-save-001",
        "steps": [{"type": "recalc"}],
    }
    job_with_save_as = {
        "schema_version": "2.0",
        "idempotency_key": "save-001",
        "steps": [{"type": "recalc"}, {"type": "save_as", "output_path": "out.xlsx"}],
    }

    for job in (job_without_save_as, job_with_save_as):
        states = simulate_transitions(job)
        assert states.index("VALIDATING") < states.index("SAVING") < states.index(
            "REOPEN_VALIDATION"
        ) < states.index("PUBLISHING")


def test_cancellation_mid_sequence_truncates_and_terminates() -> None:
    states = simulate_transitions(THREE_STEP_JOB, cancel_after_state="REFRESHING_CONNECTIONS")

    assert states == [
        "QUEUED",
        "STAGING_INPUT",
        "INSPECTING_WORKBOOK",
        "SELECTING_BACKENDS",
        "STARTING_EXCEL",
        "OPENING_WORKBOOK",
        "REFRESHING_CONNECTIONS",
        "CANCELLED",
    ]
    assert is_terminal(states[-1])
    # Nothing after the cancellation point -- recalc's CALCULATING must not appear.
    assert "CALCULATING" not in states


def test_cancellation_after_a_state_not_in_the_sequence_is_rejected() -> None:
    with pytest.raises(ContractError) as excinfo:
        simulate_transitions(THREE_STEP_JOB, cancel_after_state="RUNNING_APPROVED_MACRO")

    assert excinfo.value.code == "STATE_TRANSITION_INVALID"


def test_dry_run_output_is_pure_and_has_no_hidden_state() -> None:
    # Renamed from test_retry_with_same_idempotency_key_is_deterministic: this
    # only proves simulate_transitions() is a pure function of its input --
    # true for any pure function regardless of idempotency_key -- not that
    # idempotency_key retries are specifically handled. See the README
    # "Known gap" section for what this contract layer can and can't prove
    # about retries; test_idempotency_key_does_not_affect_the_simulated_
    # sequence_but_steps_do below is the test that actually exercises the
    # idempotency_key dimension.
    first_run = simulate_transitions(THREE_STEP_JOB)
    second_run = simulate_transitions(THREE_STEP_JOB)  # simulate re-submitting the same job

    assert first_run == second_run


def test_idempotency_key_does_not_affect_the_simulated_sequence_but_steps_do() -> None:
    # The contract-level guarantee this layer can actually make about retries:
    # resubmitting a job under a *different* idempotency_key (as a caller
    # minting a fresh key for what it believes is the same job would do) must
    # still map to the identical state sequence, because the sequence is a
    # function of `steps` only -- idempotency_key is never read by
    # simulate_transitions(). Changing `steps` instead, even under the
    # original key, must change the sequence. Together these show the field
    # is inert at this layer rather than silently ignored.
    same_steps_different_key = {**THREE_STEP_JOB, "idempotency_key": "retry-me-002"}
    assert simulate_transitions(THREE_STEP_JOB) == simulate_transitions(same_steps_different_key)

    different_steps_same_key = {
        **THREE_STEP_JOB,
        "steps": [THREE_STEP_JOB["steps"][0], THREE_STEP_JOB["steps"][1]],
    }
    assert simulate_transitions(THREE_STEP_JOB) != simulate_transitions(different_steps_same_key)


def test_unknown_step_type_cannot_be_simulated() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "bad-001",
        "steps": [{"type": "delete_everything"}],
    }

    with pytest.raises(ContractError) as excinfo:
        simulate_transitions(job)

    assert excinfo.value.code == "UNKNOWN_STEP_TYPE"
