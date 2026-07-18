"""Stage a local working copy of a workbook, then atomically publish it back.

Per RFC 0002 decision 9: stage and operate on a local copy outside any
OneDrive/SharePoint-synced path, and swap back to the original location
atomically only after validation has passed. `stage_copy` always copies into
a fresh `tempfile.mkdtemp()` directory regardless of where the source lives
-- it deliberately does not try to detect "is this path OneDrive-synced" by
path-sniffing. Always staging locally is simpler and correct for every
source location, sync-managed or not.

`publish` does not re-check invariants -- the caller must have already
confirmed validation passed (see control_plane.invariant_evaluator) before
calling it. It applies one last-ditch sanity floor instead: it refuses to
publish a staged path that doesn't exist or is empty.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .errors import ContractError


def stage_copy(source_path) -> Path:
    """Copy `source_path` into a fresh local temp directory; return the copy's path.

    Always creates a brand-new tempfile.mkdtemp() directory and copies into
    it, regardless of where `source_path` lives. Raises ContractError
    (STAGING_INVALID) if `source_path` does not exist or is not a file.
    """
    source_path = Path(source_path)
    if not source_path.is_file():
        raise ContractError(
            "STAGING_INVALID",
            f"Cannot stage a source that does not exist or is not a file: {source_path}",
            {"source_path": str(source_path)},
        )

    staging_dir = Path(tempfile.mkdtemp(prefix="xlsx-win-stage-"))
    staged_path = staging_dir / source_path.name
    shutil.copy2(source_path, staged_path)
    return staged_path


def _timestamped_backup_path(destination_path: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return destination_path.with_name(
        f"{destination_path.stem}.{timestamp}.bak{destination_path.suffix}"
    )


def publish(staged_path, destination_path) -> None:
    """Swap the already-validated staged copy into `destination_path`, atomically.

    This function does not re-check invariants -- that is the caller's job,
    via invariant_evaluator, before ever calling publish(). The only checks
    here are a last-ditch sanity floor: `staged_path` must exist and must not
    be a zero-byte file, or this raises ContractError (STAGING_INVALID).

    If a file already exists at `destination_path`, it is copied to a
    timestamped backup path alongside it before being replaced.

    Uses os.replace() for the swap when the staged file and the destination
    are on the same volume, which is atomic. When they're on different
    volumes, os.replace() cannot move across them directly; this falls back
    to copying the staged file into the destination's own directory first
    (not atomic) and then os.replace()-ing that same-directory copy onto the
    destination (atomic) -- so the swap itself is still atomic even though
    the earlier cross-volume copy wasn't.
    """
    staged_path = Path(staged_path)
    destination_path = Path(destination_path)

    if not staged_path.is_file():
        raise ContractError(
            "STAGING_INVALID",
            f"Cannot publish: staged path does not exist or is not a file: {staged_path}",
            {"staged_path": str(staged_path)},
        )
    if staged_path.stat().st_size == 0:
        raise ContractError(
            "STAGING_INVALID",
            f"Cannot publish: staged file is empty (zero bytes): {staged_path}",
            {"staged_path": str(staged_path)},
        )

    destination_path.parent.mkdir(parents=True, exist_ok=True)

    if destination_path.exists():
        shutil.copy2(destination_path, _timestamped_backup_path(destination_path))

    try:
        os.replace(staged_path, destination_path)
    except OSError:
        # Most likely a cross-volume rename (e.g. Windows "[WinError 17] The
        # system cannot move the file to a different disk drive"). Copy into
        # the destination's own directory first (not atomic), then
        # os.replace() that same-directory copy onto the destination, which
        # is atomic because both paths are now on the same volume.
        same_volume_copy = destination_path.parent / f".{destination_path.name}.incoming"
        shutil.copy2(staged_path, same_volume_copy)
        os.replace(same_volume_copy, destination_path)
