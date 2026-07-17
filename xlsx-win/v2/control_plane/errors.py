"""Normalized error taxonomy for the xlsx-win v2 contract layer.

Every error raised by this package is a ContractError carrying a
{code, message, details} shape, using one of the codes below. Callers --
especially an LLM agent -- can branch on `code` without parsing prose.
"""

from __future__ import annotations

ERROR_CODES = frozenset(
    {
        # A manifest or result document failed JSON Schema validation for a
        # reason not covered by a more specific code below.
        "SCHEMA_INVALID",
        # A step's "type" value is not one of the enumerated step types.
        "UNKNOWN_STEP_TYPE",
        # schema_version does not match the version this control plane implements.
        "MANIFEST_VERSION_MISMATCH",
        # A requested state-machine transition is not legal from the current state.
        "STATE_TRANSITION_INVALID",
        # The legacy PowerShell adapter cannot prove a manifest is equivalent to
        # the fixed legacy script behavior it would translate to.
        "LEGACY_TRANSLATION_UNSUPPORTED",
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
