from __future__ import annotations

import copy

import pytest

from control_plane.capabilities import admit_manifest, capability_inventory, load_profiles, validate_profile
from control_plane.errors import ContractError
from test_composite_contract import _manifest


def _production_append() -> dict:
    manifest = _manifest("append_table_rows")
    operation = manifest["steps"][0]
    columns = [
        {"name": "FileName", "role": "writable", "logical_type": "text"},
        {"name": "CalculatedA", "role": "calculated", "logical_type": "text"},
        *[
            {"name": f"Value{i}", "role": "writable", "logical_type": "text"}
            for i in range(2, 14)
        ],
        {"name": "CalculatedB", "role": "calculated", "logical_type": "number"},
    ]
    operation["table"].update(
        existing_body_rows=195933,
        final_body_rows=209528,
        column_count=15,
        writable_runs=2,
        columns=columns,
        saved_sort={
            "column": "FileName",
            "direction": "descending",
            "behavior": "preserve_descriptor_do_not_reapply",
        },
    )
    operation["source"].update(
        row_count=13595,
        column_count=15,
        encoded_bytes=15000000,
        text_bytes=9000000,
        cardinality=[13595] * 15,
        writable_runs=2,
    )
    operation["dependent_pivots"].update(cache_count=1, report_count=3)
    return manifest


def test_profiles_are_valid_and_experimental_before_qualification() -> None:
    profiles = load_profiles()
    assert set(profiles) == {
        "excel64_table_pivot_append_saved_sort_v1",
        "excel64_table_pivot_replace_v1",
    }
    assert all(profile["status"] == "experimental" for profile in profiles.values())
    assert all(item["sha256"] for item in capability_inventory())


def test_exact_production_append_topology_is_admitted_offline() -> None:
    admitted = admit_manifest(_production_append())
    assert admitted["profile"]["operation"] == "append_table_rows"
    assert len(admitted["sha256"]) == 64


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("source", "row_count"), 20001),
        (("source", "column_count"), 14),
        (("source", "encoded_bytes"), 268435457),
        (("dependent_pivots", "cache_count"), 6),
        (("dependent_pivots", "report_count"), 4),
    ],
)
def test_out_of_profile_manifest_fails_closed(path: tuple[str, str], value: int) -> None:
    manifest = _production_append()
    manifest["steps"][0][path[0]][path[1]] = value
    if path == ("source", "row_count"):
        manifest["steps"][0]["table"]["final_body_rows"] = 195933 + value
    if path == ("source", "column_count"):
        # Maintain schema-level agreement so this exercises profile admission.
        manifest["steps"][0]["table"]["column_count"] = value
        manifest["steps"][0]["table"]["columns"] = manifest["steps"][0]["table"]["columns"][:value]
        manifest["steps"][0]["source"]["cardinality"] = manifest["steps"][0]["source"]["cardinality"][:value]
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(manifest)
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"


def test_environment_mismatch_rejects_before_excel() -> None:
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(
            _production_append(),
            environment={
                "windows_build": "10.0.26200",
                "excel_build": "unexpected",
                "office_bitness": "x64",
                "dotnet_runtime": "10.0.10",
                "locale": "en-US",
                "date_system": "1900",
            },
        )
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"


def test_beta_label_is_impossible_without_complete_evidence() -> None:
    profile = copy.deepcopy(next(iter(load_profiles().values())))
    profile["status"] = "beta"
    with pytest.raises(ContractError) as excinfo:
        validate_profile(profile)
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
