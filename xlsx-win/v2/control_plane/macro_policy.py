"""Macro execution policy: disabled by default, exact-match allowlist only.

Per RFC 0001's security model ("approved macros allowlisted by exact
workbook hash, signature, and entrypoint") and RFC 0002 decision 6's
single-worker descoping: there is one machine and one worker here, so
"untrusted" means "reject before Excel ever touches it," not "quarantine in
a separate worker pool." This module owns the matching rule only -- it does
not load, persist, or manage the allowlist itself. Where the caller keeps
its allowlist (a config file, a database row) is that caller's concern.
"""

from __future__ import annotations

from .errors import ContractError

_REQUIRED_ENTRY_KEYS = frozenset({"workbook_sha256", "entrypoint"})


def _validate_entry(entry, index: int) -> None:
    if not isinstance(entry, dict):
        raise ContractError(
            "MACRO_ALLOWLIST_INVALID",
            f"Allowlist entry at index {index} is not an object: {entry!r}.",
            {"index": index},
        )
    missing = sorted(_REQUIRED_ENTRY_KEYS - entry.keys())
    if missing:
        raise ContractError(
            "MACRO_ALLOWLIST_INVALID",
            f"Allowlist entry at index {index} is missing required key(s): {missing}.",
            {"index": index, "missing": missing},
        )


def is_macro_approved(workbook_sha256: str, macro_name: str, allowlist: list) -> bool:
    """True iff (workbook_sha256, macro_name) exactly matches an allowlist entry.

    `allowlist` is a list of {"workbook_sha256": str, "entrypoint": str}
    objects. Matching is exact: case-sensitive, no wildcards, no prefix or
    substring matching -- this is a security boundary, and ambiguity here is
    a vulnerability, not a convenience feature.

    Raises ContractError (MACRO_ALLOWLIST_INVALID) if any entry is malformed,
    rather than silently skipping it: a silently-skipped malformed entry
    could otherwise mask a broken allowlist config behind an always-false
    result, which looks safe but isn't trustworthy.
    """
    for index, entry in enumerate(allowlist):
        _validate_entry(entry, index)
        if entry["workbook_sha256"] == workbook_sha256 and entry["entrypoint"] == macro_name:
            return True
    return False
