#!/usr/bin/env python3
"""Regression tests for the exact scenario resolver."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("resolve_scenario.py")
SPEC = importlib.util.spec_from_file_location("scenario_resolver", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT}")
RESOLVER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RESOLVER
SPEC.loader.exec_module(RESOLVER)


def test_opus_alias_resolves_controlled_profile() -> None:
    result = RESOLVER.build_resolution("claude-code", "Opus 4.8")
    assert result["scenario_id"] == "claude-code-opus-4.8"
    assert result["orchestration"]["capability_selection"] == "router_preselected"
    assert result["orchestration"]["gate_density"] == "high"


def test_sonnet_is_distinct_from_opus() -> None:
    result = RESOLVER.build_resolution("claude-code", "Sonnet 5")
    assert result["scenario_id"] == "claude-code-sonnet-5"
    assert result["orchestration"]["gate_density"] == "medium"
    assert result["orchestration"]["max_repair_attempts"] == 2


def test_sol_resolves_adaptive_codex_profile() -> None:
    result = RESOLVER.build_resolution("codex", "GPT 5.6 Sol", "autonomous")
    assert result["scenario_id"] == "codex-gpt-5.6-sol"
    assert result["orchestration"]["capability_selection"] == "adaptive_within_approved_graph"
    assert result["orchestration"]["provider_loading"] == "lazy"


def test_wrong_harness_does_not_infer_nearby_scenario() -> None:
    try:
        RESOLVER.build_resolution("claude-code", "GPT-5.6 Sol")
    except RESOLVER.ScenarioResolutionError as exc:
        assert "unsupported harness/model pair" in str(exc)
    else:
        raise AssertionError("unsupported pair unexpectedly resolved")


def test_selected_capabilities_are_preserved_and_deduplicated() -> None:
    result = RESOLVER.build_resolution(
        "codex",
        "Sol 5.6",
        capabilities=["repository_mapping", "repository_mapping", "implementation_planning"],
    )
    assert result["selected_capabilities"] == ["repository_mapping", "implementation_planning"]
    assert "dachent.repo-map-codex" in result["provider_candidates"]["repository_mapping"]


def test_provider_validation_is_harness_aware() -> None:
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "bindings.json"
        path.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "capabilities": [
                        {
                            "name": "implementation_planning",
                            "providers": [
                                {
                                    "id": "claude-only",
                                    "harnesses": ["claude-code"],
                                    "invocation_mode": "model",
                                    "entrypoint_candidates": ["x/SKILL.md"],
                                }
                            ],
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        try:
            RESOLVER.build_resolution(
                "codex",
                "gpt-5.6-sol",
                capabilities=["implementation_planning"],
                bindings_path=path,
            )
        except RESOLVER.ScenarioResolutionError as exc:
            assert "no codex provider" in str(exc)
        else:
            raise AssertionError("wrong-harness provider unexpectedly satisfied preflight")


def test_policy_floor_is_returned_unchanged() -> None:
    data = RESOLVER.load_profiles()
    result = RESOLVER.build_resolution("claude-code", "opus-4.8")
    assert result["policy_floor"] == data["policy_floor"]
    assert result["policy_floor"]["silent_required_provider_fallback"] == "forbidden"


def main() -> int:
    tests = [
        test_opus_alias_resolves_controlled_profile,
        test_sonnet_is_distinct_from_opus,
        test_sol_resolves_adaptive_codex_profile,
        test_wrong_harness_does_not_infer_nearby_scenario,
        test_selected_capabilities_are_preserved_and_deduplicated,
        test_provider_validation_is_harness_aware,
        test_policy_floor_is_returned_unchanged,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} scenario resolver regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
