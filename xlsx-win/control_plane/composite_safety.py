"""Fail-closed cleanup and publication primitives for composite jobs."""

from __future__ import annotations

import json
import os
import shutil
import uuid
from pathlib import Path

from .errors import ContractError
from .ooxml_verifier import sha256_path


def cleanup_from_native_result(result: dict) -> dict[str, bool]:
    """Accept cleanup only from an explicit supervisor-owned-process proof."""

    complete = False
    for invariant in result.get("invariants", []):
        if not isinstance(invariant, dict) or invariant.get("passed") is not True:
            continue
        name = invariant.get("name")
        message = str(invariant.get("message", ""))
        if name == "supervisor_owned_processes_zero" and "active_owned_processes=0" in message:
            complete = True
        if (
            name == "supervisor_owned_process_cleanup"
            and "owned_processes_zero=true" in message
            and "termination_verified=true" in message
        ):
            complete = True
    return {
        "owned_processes_zero": complete,
        "worker_exit_verified": complete,
        "excel_exit_verified": complete,
        "termination_verified": complete,
    }


def write_json_atomic(path: Path, value: object) -> None:
    """Replace a JSON result with same-directory atomic rename semantics."""

    path.parent.mkdir(parents=True, exist_ok=True)
    incoming = path.with_name(f".{path.name}.{uuid.uuid4().hex}.incoming")
    try:
        incoming.write_text(
            json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(incoming, path)
    finally:
        incoming.unlink(missing_ok=True)


class AtomicPublication:
    """Publish verified bytes and restore the prior destination on any failure."""

    def __init__(self, destination: Path, original_sha256: str | None) -> None:
        self.destination = destination
        self.original_sha256 = original_sha256
        token = uuid.uuid4().hex
        self.incoming = destination.with_name(f".{destination.name}.{token}.incoming")
        self.rollback_copy = destination.with_name(f".{destination.name}.{token}.rollback")
        self._published = False
        self._committed = False

    def __enter__(self) -> "AtomicPublication":
        return self

    def publish(self, staged: Path) -> str:
        if not staged.is_file() or staged.stat().st_size == 0:
            raise ContractError(
                "STAGING_INVALID",
                "Verified staged output is missing or empty at publication.",
                {"staged_path": str(staged)},
            )
        self.destination.parent.mkdir(parents=True, exist_ok=True)
        if self.destination.exists() and not self.destination.is_file():
            raise ContractError(
                "STAGING_INVALID",
                "Composite output destination exists but is not a file.",
                {"destination": str(self.destination)},
            )

        staged_hash = sha256_path(staged)
        shutil.copy2(staged, self.incoming)
        if sha256_path(self.incoming) != staged_hash:
            raise ContractError(
                "RESULT_PROOF_INVALID",
                "Same-volume publication copy differs from verified staged bytes.",
                {},
            )
        if self.destination.is_file():
            shutil.copy2(self.destination, self.rollback_copy)
            if sha256_path(self.rollback_copy) != self.original_sha256:
                raise ContractError(
                    "RESULT_PROOF_INVALID",
                    "Rollback copy differs from the transaction-start destination.",
                    {},
                )
        os.replace(self.incoming, self.destination)
        self._published = True
        return sha256_path(self.destination)

    def commit(self) -> None:
        if not self._published:
            raise ContractError("RESULT_PROOF_INVALID", "Publication was not performed.", {})
        self.rollback_copy.unlink(missing_ok=True)
        self._committed = True

    def _rollback(self) -> None:
        self.incoming.unlink(missing_ok=True)
        if not self._published:
            self.rollback_copy.unlink(missing_ok=True)
            return
        if self.rollback_copy.is_file():
            os.replace(self.rollback_copy, self.destination)
        else:
            self.destination.unlink(missing_ok=True)
        restored_hash = sha256_path(self.destination) if self.destination.is_file() else None
        if restored_hash != self.original_sha256:
            raise ContractError(
                "RESULT_PROOF_INVALID",
                "Destination rollback did not restore the transaction-start bytes.",
                {"expected": self.original_sha256, "actual": restored_hash},
            )

    def __exit__(self, exc_type, exc, traceback) -> bool:
        if exc_type is not None or not self._committed:
            self._rollback()
        else:
            self.incoming.unlink(missing_ok=True)
            self.rollback_copy.unlink(missing_ok=True)
        return False
