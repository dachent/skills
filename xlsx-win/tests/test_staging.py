"""Staging tests (issue #38 / RFC 0002 decision 9).

Covers: stage_copy always stages into a fresh local temp directory
regardless of source location; publish() is a last-ditch sanity floor
(refuses empty/missing staged files) and takes a timestamped backup of any
existing destination before swapping; the swap is atomic via os.replace()
on the same volume, and via a same-directory copy-then-replace fallback
when the staged file and destination are on different volumes.
"""

from __future__ import annotations

import os
import shutil
import string
import tempfile
from pathlib import Path

import pytest

from control_plane.errors import ContractError
from control_plane.staging import publish, stage_copy


def test_stage_copy_creates_a_fresh_local_copy(tmp_path) -> None:
    source = tmp_path / "source.xlsx"
    source.write_bytes(b"workbook-bytes")

    staged = stage_copy(source)

    assert staged.exists()
    assert staged.read_bytes() == b"workbook-bytes"
    assert staged.parent != source.parent  # copied into its own fresh directory
    assert staged.name == source.name


def test_stage_copy_stages_regardless_of_source_location(tmp_path) -> None:
    # No OneDrive/SharePoint path-sniffing: any two distinct source
    # directories must each get their own fresh staging directory.
    source_a = tmp_path / "a" / "wb.xlsx"
    source_a.parent.mkdir()
    source_a.write_bytes(b"a")
    source_b = tmp_path / "b" / "wb.xlsx"
    source_b.parent.mkdir()
    source_b.write_bytes(b"b")

    staged_a = stage_copy(source_a)
    staged_b = stage_copy(source_b)

    assert staged_a.parent != staged_b.parent
    assert staged_a.read_bytes() == b"a"
    assert staged_b.read_bytes() == b"b"


def test_stage_copy_rejects_missing_source(tmp_path) -> None:
    with pytest.raises(ContractError) as excinfo:
        stage_copy(tmp_path / "does_not_exist.xlsx")

    assert excinfo.value.code == "STAGING_INVALID"


def test_stage_copy_rejects_a_directory_as_source(tmp_path) -> None:
    directory = tmp_path / "a_directory"
    directory.mkdir()

    with pytest.raises(ContractError) as excinfo:
        stage_copy(directory)

    assert excinfo.value.code == "STAGING_INVALID"


def test_publish_refuses_empty_staged_file(tmp_path) -> None:
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"")  # zero bytes
    destination = tmp_path / "dest.xlsx"

    with pytest.raises(ContractError) as excinfo:
        publish(staged, destination)

    assert excinfo.value.code == "STAGING_INVALID"
    assert not destination.exists()


def test_publish_refuses_missing_staged_file(tmp_path) -> None:
    with pytest.raises(ContractError) as excinfo:
        publish(tmp_path / "does_not_exist.xlsx", tmp_path / "dest.xlsx")

    assert excinfo.value.code == "STAGING_INVALID"


def test_publish_same_volume_replaces_destination_and_backs_up_existing(tmp_path) -> None:
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"new-content")
    destination = tmp_path / "dest.xlsx"
    destination.write_bytes(b"old-content")

    publish(staged, destination)

    assert destination.read_bytes() == b"new-content"
    backups = list(tmp_path.glob("dest.*.bak.xlsx"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"old-content"


def test_publish_with_no_existing_destination_creates_no_backup(tmp_path) -> None:
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"content")
    destination = tmp_path / "dest.xlsx"

    publish(staged, destination)

    assert destination.read_bytes() == b"content"
    assert list(tmp_path.glob("dest.*.bak.xlsx")) == []


def test_publish_creates_destination_directory_if_missing(tmp_path) -> None:
    staged = tmp_path / "staged.xlsx"
    staged.write_bytes(b"content")
    destination = tmp_path / "nested" / "dir" / "dest.xlsx"

    publish(staged, destination)

    assert destination.read_bytes() == b"content"


def _writable_second_volume() -> Path | None:
    """Find a writable directory root on a fixed volume different from tempfile's.

    stage_copy() always stages into tempfile.gettempdir()'s volume. To
    exercise the genuine cross-volume fallback branch in staging.publish
    (rather than faking a volume difference that isn't real), this looks
    for another local drive letter that actually exists and is writable on
    this machine.
    """
    tmp_drive = Path(tempfile.gettempdir()).resolve().drive.upper()
    for letter in string.ascii_uppercase:
        root = Path(f"{letter}:/")
        if not root.exists() or root.drive.upper() == tmp_drive:
            continue
        probe = root / f".xlsx_win_v2_staging_probe_{os.getpid()}"
        try:
            probe.mkdir()
        except OSError:
            continue
        probe.rmdir()
        return root
    return None


def test_publish_across_different_volumes_falls_back_to_copy_then_atomic_replace(
    tmp_path,
) -> None:
    # The staged copy comes from the module under test's own stage_copy(),
    # which always lands on tempfile.gettempdir()'s volume. The destination
    # is deliberately placed on a genuinely different writable fixed volume,
    # if this machine has one, so os.replace() cannot move it directly and
    # the copy-then-replace fallback in staging.publish is what actually
    # executes -- not a same-volume path dressed up as "different".
    #
    # If this machine has no second writable fixed volume (e.g. a
    # single-disk CI runner), this is skipped rather than faked: there is no
    # way to make os.replace() genuinely cross a volume boundary without one.
    second_volume = _writable_second_volume()
    if second_volume is None:
        pytest.skip(
            "No second writable fixed volume available on this machine to test a "
            "genuine cross-volume publish; skipping honestly rather than faking "
            "a volume difference that isn't real."
        )

    source = tmp_path / "source.xlsx"
    source.write_bytes(b"cross-volume-content")
    staged = stage_copy(source)
    assert staged.drive.upper() != second_volume.drive.upper()  # genuinely different volumes

    dest_dir = Path(tempfile.mkdtemp(dir=str(second_volume)))
    try:
        destination = dest_dir / "dest.xlsx"

        publish(staged, destination)

        assert destination.read_bytes() == b"cross-volume-content"
        # No stray same-directory ".incoming" temp file left behind.
        assert list(dest_dir.iterdir()) == [destination]
    finally:
        shutil.rmtree(dest_dir, ignore_errors=True)
