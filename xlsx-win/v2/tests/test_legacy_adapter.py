"""Legacy PowerShell compatibility adapter tests.

Covers the original #34 acceptance criterion "Existing PowerShell entrypoints
can be invoked through a temporary compatibility adapter" for
refresh_excel.ps1, without shelling out to PowerShell -- only the argument
translation is exercised here.
"""

from __future__ import annotations

import pytest

from control_plane.errors import ContractError
from control_plane.legacy_adapter import REFRESH_EXCEL_SCRIPT, translate_refresh_and_recalc

TRANSLATABLE_JOB = {
    "schema_version": "2.0",
    "idempotency_key": "legacy-001",
    "steps": [
        {"type": "open", "workbook_path": "C:\\jobs\\input\\model.xlsx"},
        {"type": "refresh", "connections": "all"},
        {"type": "recalc"},
    ],
}


def test_translates_the_canonical_open_refresh_all_recalc_shape() -> None:
    translated = translate_refresh_and_recalc(TRANSLATABLE_JOB)

    assert translated == {
        "script": REFRESH_EXCEL_SCRIPT,
        "arguments": [
            "-WorkbookPath",
            "C:\\jobs\\input\\model.xlsx",
            "-TimeoutSeconds",
            "1800",
        ],
    }


def test_honors_an_explicit_recalc_timeout() -> None:
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            TRANSLATABLE_JOB["steps"][0],
            TRANSLATABLE_JOB["steps"][1],
            {"type": "recalc", "timeout_seconds": 60},
        ],
    }

    translated = translate_refresh_and_recalc(job)

    assert translated["arguments"] == [
        "-WorkbookPath",
        "C:\\jobs\\input\\model.xlsx",
        "-TimeoutSeconds",
        "60",
    ]


def test_rejects_a_schema_invalid_manifest() -> None:
    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc({"schema_version": "2.0", "idempotency_key": "x", "steps": []})

    assert excinfo.value.code == "SCHEMA_INVALID"


def test_rejects_wrong_step_count() -> None:
    job = {
        "schema_version": "2.0",
        "idempotency_key": "legacy-002",
        "steps": [TRANSLATABLE_JOB["steps"][0], TRANSLATABLE_JOB["steps"][1]],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_read_only_open_because_legacy_script_always_saves() -> None:
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            {**TRANSLATABLE_JOB["steps"][0], "read_only": True},
            TRANSLATABLE_JOB["steps"][1],
            TRANSLATABLE_JOB["steps"][2],
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_update_links_true_because_legacy_script_never_updates_links() -> None:
    # refresh_excel.ps1 unconditionally sets AskToUpdateLinks=$false and opens
    # with UpdateLinks=0; it can never honor a link-update request, so this
    # must be rejected rather than silently translated as if it were honored.
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            {**TRANSLATABLE_JOB["steps"][0], "update_links": True},
            TRANSLATABLE_JOB["steps"][1],
            TRANSLATABLE_JOB["steps"][2],
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_partial_connection_list_as_unsafe_overreach() -> None:
    # refresh_excel.ps1 always calls RefreshAll(); translating a job that asked
    # for only specific connections would refresh MORE than requested.
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            TRANSLATABLE_JOB["steps"][0],
            {"type": "refresh", "connections": ["SalesDB"]},
            TRANSLATABLE_JOB["steps"][2],
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_non_full_rebuild_recalc_mode() -> None:
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            TRANSLATABLE_JOB["steps"][0],
            TRANSLATABLE_JOB["steps"][1],
            {"type": "recalc", "mode": "normal"},
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_extra_trailing_step() -> None:
    # refresh_excel.ps1 has no macro hook and does not save-as.
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            *TRANSLATABLE_JOB["steps"],
            {"type": "save_as", "output_path": "out.xlsx"},
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"


def test_rejects_wrong_step_order() -> None:
    job = {
        **TRANSLATABLE_JOB,
        "steps": [
            TRANSLATABLE_JOB["steps"][1],
            TRANSLATABLE_JOB["steps"][0],
            TRANSLATABLE_JOB["steps"][2],
        ],
    }

    with pytest.raises(ContractError) as excinfo:
        translate_refresh_and_recalc(job)

    assert excinfo.value.code == "LEGACY_TRANSLATION_UNSUPPORTED"
