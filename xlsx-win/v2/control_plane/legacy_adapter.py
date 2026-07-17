"""Translate a subset of v2 job manifests into legacy PowerShell invocations.

Migration-only shim (original #34 acceptance criterion: existing PowerShell
entrypoints must remain invokable through the new contract). Scope is
deliberately narrow: only a job shaped exactly like refresh_excel.ps1's fixed
behavior -- open the workbook, RefreshAll(), CalculateFullRebuild(), save in
place, macros disabled -- can be translated. Anything this adapter cannot
prove is equivalent to that behavior is rejected rather than translated
loosely. This module never shells out to PowerShell itself; it only produces
the argument list a caller would pass to it.
"""

from __future__ import annotations

from .errors import ContractError
from .schemas import validate_job

REFRESH_EXCEL_SCRIPT = "refresh_excel.ps1"
_DEFAULT_TIMEOUT_SECONDS = 1800


def _unsupported(message: str, details: dict) -> ContractError:
    return ContractError("LEGACY_TRANSLATION_UNSUPPORTED", message, details)


def translate_refresh_and_recalc(job: dict) -> dict:
    """Translate a job into the refresh_excel.ps1 invocation shape.

    Returns {"script": "refresh_excel.ps1", "arguments": [...]}. Raises
    ContractError (SCHEMA_INVALID or LEGACY_TRANSLATION_UNSUPPORTED) if the
    job is malformed or is not provably equivalent to refresh_excel.ps1.
    """
    validate_job(job)

    steps = job["steps"]
    if len(steps) != 3:
        raise _unsupported(
            "refresh_excel.ps1 only maps to a fixed [open, refresh, recalc] shape; "
            f"got {len(steps)} step(s).",
            {"step_count": len(steps)},
        )

    open_step, refresh_step, recalc_step = steps

    if open_step["type"] != "open":
        raise _unsupported(
            "First step must be 'open'.", {"step_index": 0, "type": open_step["type"]}
        )
    if open_step.get("read_only"):
        raise _unsupported(
            "refresh_excel.ps1 always saves the workbook in place; an 'open' step "
            "with read_only=true cannot be translated.",
            {"step_index": 0},
        )
    if open_step.get("update_links"):
        raise _unsupported(
            "refresh_excel.ps1 always opens with UpdateLinks=0/AskToUpdateLinks=False; "
            "an 'open' step requesting update_links=true cannot be translated.",
            {"step_index": 0},
        )

    if refresh_step["type"] != "refresh":
        raise _unsupported(
            "Second step must be 'refresh'.", {"step_index": 1, "type": refresh_step["type"]}
        )
    if refresh_step["connections"] != "all":
        raise _unsupported(
            "refresh_excel.ps1 always refreshes every connection via RefreshAll(); "
            "a manifest requesting a specific connection list cannot be safely "
            "translated, since that would refresh more than it asked for.",
            {"step_index": 1, "connections": refresh_step["connections"]},
        )

    if recalc_step["type"] != "recalc":
        raise _unsupported(
            "Third step must be 'recalc'.", {"step_index": 2, "type": recalc_step["type"]}
        )
    mode = recalc_step.get("mode", "full_rebuild")
    if mode != "full_rebuild":
        raise _unsupported(
            f"refresh_excel.ps1 always performs CalculateFullRebuild(); recalc mode "
            f"{mode!r} cannot be translated.",
            {"step_index": 2, "mode": mode},
        )

    timeout_seconds = recalc_step.get("timeout_seconds", _DEFAULT_TIMEOUT_SECONDS)

    return {
        "script": REFRESH_EXCEL_SCRIPT,
        "arguments": [
            "-WorkbookPath",
            open_step["workbook_path"],
            "-TimeoutSeconds",
            str(timeout_seconds),
        ],
    }
