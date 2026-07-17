"""Macro policy tests (issue #38): exact-match allowlist only.

Covers the acceptance criteria "unknown macros ... are rejected before Excel
execution" and "an unapproved macro rejected and an approved one accepted",
descoped per RFC 0002 to a pure allowlist-membership check (this module
owns matching only, not persistence or a worker pool).
"""

from __future__ import annotations

import pytest

from control_plane.errors import ContractError
from control_plane.macro_policy import is_macro_approved

ALLOWLIST = [
    {"workbook_sha256": "abc123", "entrypoint": "RefreshDashboard"},
    {"workbook_sha256": "def456", "entrypoint": "ExportReport"},
]


def test_approved_macro_is_accepted() -> None:
    assert is_macro_approved("abc123", "RefreshDashboard", ALLOWLIST) is True


def test_unapproved_macro_is_rejected_for_wrong_workbook() -> None:
    assert is_macro_approved("zzz999", "RefreshDashboard", ALLOWLIST) is False


def test_unapproved_macro_is_rejected_for_wrong_entrypoint() -> None:
    assert is_macro_approved("abc123", "DeleteEverything", ALLOWLIST) is False


def test_matching_is_case_sensitive() -> None:
    assert is_macro_approved("abc123", "refreshdashboard", ALLOWLIST) is False
    assert is_macro_approved("ABC123", "RefreshDashboard", ALLOWLIST) is False


def test_no_prefix_or_substring_matching() -> None:
    assert is_macro_approved("abc123", "RefreshDashboardExtra", ALLOWLIST) is False
    assert is_macro_approved("abc1234", "RefreshDashboard", ALLOWLIST) is False
    assert is_macro_approved("abc12", "RefreshDashboard", ALLOWLIST) is False


def test_empty_allowlist_rejects_everything() -> None:
    assert is_macro_approved("abc123", "RefreshDashboard", []) is False


def test_malformed_entry_missing_required_key_raises_contract_error() -> None:
    bad_allowlist = [{"workbook_sha256": "abc123"}]  # missing entrypoint

    with pytest.raises(ContractError) as excinfo:
        is_macro_approved("abc123", "RefreshDashboard", bad_allowlist)

    assert excinfo.value.code == "MACRO_ALLOWLIST_INVALID"
    assert excinfo.value.details["missing"] == ["entrypoint"]


def test_malformed_entry_that_is_not_an_object_raises_contract_error() -> None:
    with pytest.raises(ContractError) as excinfo:
        is_macro_approved("abc123", "RefreshDashboard", ["not-a-dict"])

    assert excinfo.value.code == "MACRO_ALLOWLIST_INVALID"


def test_malformed_entry_is_not_silently_skipped_even_if_a_later_entry_would_match() -> None:
    # A malformed entry must raise, not be skipped -- silently skipping it
    # could mask a broken allowlist behind an always-false result.
    allowlist = [{"workbook_sha256": "abc123"}, {"workbook_sha256": "abc123", "entrypoint": "X"}]

    with pytest.raises(ContractError):
        is_macro_approved("abc123", "X", allowlist)
