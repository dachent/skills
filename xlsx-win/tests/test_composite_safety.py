from __future__ import annotations

import json

import pytest

from control_plane.composite_safety import (
    AtomicPublication,
    cleanup_from_native_result,
    write_json_atomic,
)
from control_plane.errors import ContractError
from control_plane.ooxml_verifier import sha256_path


def _invariant(name: str, passed: bool, message: str) -> dict:
    return {"name": name, "passed": passed, "message": message}


def test_cleanup_requires_explicit_supervisor_attestation() -> None:
    missing = cleanup_from_native_result({"invariants": []})
    incomplete = cleanup_from_native_result(
        {"invariants": [_invariant("supervisor_owned_process_cleanup", True, "termination_verified=true")]}
    )
    success = cleanup_from_native_result(
        {"invariants": [_invariant("supervisor_owned_processes_zero", True, "active_owned_processes=0")]}
    )
    terminated = cleanup_from_native_result(
        {
            "invariants": [
                _invariant(
                    "supervisor_owned_process_cleanup",
                    True,
                    "termination_verified=true; owned_processes_zero=true",
                )
            ]
        }
    )

    assert not any(missing.values())
    assert not any(incomplete.values())
    assert all(success.values())
    assert all(terminated.values())


def test_publication_commit_replaces_destination_and_removes_rollback_files(tmp_path) -> None:
    destination = tmp_path / "published.xlsx"
    staged = tmp_path / "staged.xlsx"
    destination.write_bytes(b"before")
    staged.write_bytes(b"after")

    with AtomicPublication(destination, sha256_path(destination)) as publication:
        assert publication.publish(staged) == sha256_path(staged)
        publication.commit()

    assert destination.read_bytes() == b"after"
    assert list(tmp_path.glob(".*.incoming")) == []
    assert list(tmp_path.glob(".*.rollback")) == []


def test_publication_rolls_back_existing_destination_on_late_failure(tmp_path) -> None:
    destination = tmp_path / "published.xlsx"
    staged = tmp_path / "staged.xlsx"
    destination.write_bytes(b"before")
    staged.write_bytes(b"after")

    with pytest.raises(RuntimeError, match="late proof failure"):
        with AtomicPublication(destination, sha256_path(destination)) as publication:
            publication.publish(staged)
            raise RuntimeError("late proof failure")

    assert destination.read_bytes() == b"before"


def test_publication_removes_new_destination_on_late_failure(tmp_path) -> None:
    destination = tmp_path / "published.xlsx"
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"after")

    with pytest.raises(RuntimeError):
        with AtomicPublication(destination, None) as publication:
            publication.publish(staged)
            raise RuntimeError("late proof failure")

    assert not destination.exists()


def test_publication_refuses_stale_original_binding_before_replace(tmp_path) -> None:
    destination = tmp_path / "published.xlsx"
    staged = tmp_path / "staged.xlsx"
    destination.write_bytes(b"changed")
    staged.write_bytes(b"after")

    with pytest.raises(ContractError, match="Rollback copy differs"):
        with AtomicPublication(destination, "0" * 64) as publication:
            publication.publish(staged)

    assert destination.read_bytes() == b"changed"


def test_atomic_result_writer_replaces_complete_json(tmp_path) -> None:
    result = tmp_path / "result.json"
    result.write_text("stale", encoding="utf-8")
    write_json_atomic(result, {"ok": True, "value": 3})

    assert json.loads(result.read_text(encoding="utf-8")) == {"ok": True, "value": 3}
    assert list(tmp_path.glob(".*.incoming")) == []
