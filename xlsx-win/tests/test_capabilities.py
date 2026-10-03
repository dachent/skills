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


def _append_environment(excel_build: str) -> dict:
    return {
        "windows_build": "10.0.26200",
        "excel_build": excel_build,
        "office_bitness": "x64",
        "dotnet_runtime": "10.0.10",
        "locale": "en-US",
        "date_system": "1900",
    }


def test_min_excel_build_floor_admits_equal_and_above() -> None:
    # Floor (16.0.20313.20000) and every certified build pass without warning.
    for build in ("16.0.20313.20000", "16.0.20326.20000", "16.0.20330.20000"):
        admitted = admit_manifest(_production_append(), environment=_append_environment(build))
        assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"


def test_min_excel_build_floor_rejects_below() -> None:
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment("16.0.20312.20000"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    assert any(failure["check"] == "excel_build" for failure in excinfo.value.details["failures"])


def test_uncertified_build_above_floor_warns_and_proceeds(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admitted = admit_manifest(_production_append(), environment=_append_environment("16.0.20331.20000"))
    assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("uncertified Excel build 16.0.20331.20000" in record.getMessage() for record in warnings)


def test_certified_build_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admit_manifest(_production_append(), environment=_append_environment("16.0.20330.20000"))
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


def test_legacy_profile_without_floor_keeps_exact_match(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = copy.deepcopy(load_profiles()["excel64_table_pivot_append_saved_sort_v1"])
    del profile["environment"]["min_excel_build"]
    monkeypatch.setattr(
        "control_plane.capabilities.load_profiles",
        lambda: {profile["id"]: profile},
    )
    # Certified build still passes.
    admit_manifest(_production_append(), environment=_append_environment("16.0.20313.20000"))
    # Anything outside excel_builds -- even a newer build -- is rejected,
    # exactly as before.
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment("16.0.20331.20000"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    assert any(failure["check"] == "excel_build" for failure in excinfo.value.details["failures"])


def _append_environment_dotnet(dotnet_runtime: str) -> dict:
    env = _append_environment("16.0.20330.20000")
    env["dotnet_runtime"] = dotnet_runtime
    return env


def test_min_dotnet_runtime_floor_admits_equal_and_above() -> None:
    # Floor (10.0.10) and the certified runtime pass without warning; a
    # servicing update above the floor (the 2026-08-12 10.0.10 -> 10.0.11
    # auto-update that blocked all production trend #7 jobs) also passes.
    for runtime in ("10.0.10", "10.0.11", "10.1.0"):
        admitted = admit_manifest(_production_append(), environment=_append_environment_dotnet(runtime))
        assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"


def test_min_dotnet_runtime_floor_rejects_below() -> None:
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment_dotnet("10.0.9"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    assert any(failure["check"] == "dotnet_runtime" for failure in excinfo.value.details["failures"])


def test_uncertified_dotnet_above_floor_warns_and_proceeds(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admitted = admit_manifest(_production_append(), environment=_append_environment_dotnet("10.0.11"))
    assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("uncertified .NET runtime 10.0.11" in record.getMessage() for record in warnings)


def test_certified_dotnet_does_not_warn(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admit_manifest(_production_append(), environment=_append_environment_dotnet("10.0.10"))
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


def test_legacy_profile_without_dotnet_floor_keeps_exact_match(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = copy.deepcopy(load_profiles()["excel64_table_pivot_append_saved_sort_v1"])
    del profile["environment"]["min_dotnet_runtime"]
    monkeypatch.setattr(
        "control_plane.capabilities.load_profiles",
        lambda: {profile["id"]: profile},
    )
    # Certified runtime still passes.
    admit_manifest(_production_append(), environment=_append_environment_dotnet("10.0.10"))
    # Anything other than the exact pin -- even a newer runtime -- is
    # rejected, exactly as before.
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment_dotnet("10.0.11"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    assert any(failure["check"] == "dotnet_runtime" for failure in excinfo.value.details["failures"])


def test_beta_label_is_impossible_without_complete_evidence() -> None:
    profile = copy.deepcopy(next(iter(load_profiles().values())))
    profile["status"] = "beta"
    with pytest.raises(ContractError) as excinfo:
        validate_profile(profile)
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"


# ---------------------------------------------------------------------------
# WKFINOPS-552 (2026-10-02): windows_build FLOOR semantics — the
# exact-membership windows_builds gate becomes a floor (mirrors the 435 excel
# / 461 dotnet floors; the third environment-drift instance). The
# windows_builds list stays as the PROVEN-set record: 26200 is the only build
# with a completed composite job (2026-09-30); the 2026-10-02 WKFINOPS-232
# fiat list-admission of the then-new 26300 is superseded — a build at/above
# the floor but outside the proven set WARNs and proceeds (the live smoke
# qualifies it), below the floor it fails closed.
# ---------------------------------------------------------------------------


def _append_environment_windows(windows_build: str) -> dict:
    env = _append_environment_dotnet("10.0.10")
    env["windows_build"] = windows_build
    return env


def test_both_pivot_profiles_declare_the_windows_floor() -> None:
    for profile in load_profiles().values():
        env = profile["environment"]
        assert env["min_windows_build"] == "10.0.26200"
        # the proven-set record keeps the proven build; the floor is the gate
        assert "10.0.26200" in env["windows_builds"]


def test_windows_build_26300_admitted_with_warning(caplog: pytest.LogCaptureFixture) -> None:
    # the current host build (the 2026-10-02 26200 -> 26300 feature update that
    # tripped the exact-membership gate): at/above the floor, outside the proven
    # set -> admitted WITH the warning, not silently.
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admitted = admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26300"))
    assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any(
        "uncertified newer build 10.0.26300" in record.getMessage()
        and "the live smoke qualifies it" in record.getMessage()
        for record in warnings
    )


def test_proven_windows_build_passes_silently(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admitted = admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26200"))
    assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"
    assert not [record for record in caplog.records if record.levelname == "WARNING"]


def test_windows_build_below_floor_fails_closed() -> None:
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26100"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    failure = excinfo.value.details["failures"][0]
    assert failure["check"] == "windows_build"
    assert failure["actual"] == "10.0.26100"
    assert failure["allowed"] == {"min_windows_build": "10.0.26200"}


def test_unknown_windows_build_above_floor_warns_and_proceeds(caplog: pytest.LogCaptureFixture) -> None:
    # the WKFINOPS-232 test_unknown_windows_build_still_fail_closed semantics
    # moved: a future unknown build (the next 26Hx feature update) is at or
    # above the floor and proceeds with a WARN instead of blocking every job.
    with caplog.at_level("WARNING", logger="control_plane.capabilities"):
        admitted = admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26999"))
    assert admitted["profile"]["id"] == "excel64_table_pivot_append_saved_sort_v1"
    warnings = [record for record in caplog.records if record.levelname == "WARNING"]
    assert any("uncertified newer build 10.0.26999" in record.getMessage() for record in warnings)


def test_legacy_profile_without_windows_floor_keeps_exact_match(monkeypatch: pytest.MonkeyPatch) -> None:
    profile = copy.deepcopy(load_profiles()["excel64_table_pivot_append_saved_sort_v1"])
    del profile["environment"]["min_windows_build"]
    monkeypatch.setattr(
        "control_plane.capabilities.load_profiles",
        lambda: {profile["id"]: profile},
    )
    # the proven build still passes.
    admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26200"))
    # anything outside windows_builds -- even a newer build -- is rejected,
    # exactly as before.
    with pytest.raises(ContractError) as excinfo:
        admit_manifest(_production_append(), environment=_append_environment_windows("10.0.26300"))
    assert excinfo.value.code == "CAPABILITY_PROFILE_INVALID"
    assert any(failure["check"] == "windows_build" for failure in excinfo.value.details["failures"])
