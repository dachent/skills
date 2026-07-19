"""Normalized error taxonomy for the xlsx-win contract layer."""

from __future__ import annotations

ERROR_CODES = frozenset(
    {
        "SCHEMA_INVALID",
        "UNKNOWN_STEP_TYPE",
        "COMPOSITE_SEMANTICS_INVALID",
        "COMPOSITE_RUNTIME_UNAVAILABLE",
        "RESULT_VERSION_MISMATCH",
        "RESULT_PROOF_INVALID",
        "CAPABILITY_PROFILE_INVALID",
        "MANIFEST_VERSION_MISMATCH",
        "STATE_TRANSITION_INVALID",
        "LEGACY_TRANSLATION_UNSUPPORTED",
        "WORKBOOK_UNREADABLE",
        "MACRO_ALLOWLIST_INVALID",
        "STAGING_INVALID",
        "AUDIT_SOURCE_MISSING",
        "SUPERVISOR_INVOCATION_FAILED",
    }
)


class ContractError(Exception):
    """A normalized contract-layer error: {code, message, details}."""

    def __init__(self, code: str, message: str, details: dict | None = None) -> None:
        if code not in ERROR_CODES:
            raise ValueError(f"Unknown error code: {code!r}. Known codes: {sorted(ERROR_CODES)}")
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict:
        return {"code": self.code, "message": self.message, "details": self.details}
