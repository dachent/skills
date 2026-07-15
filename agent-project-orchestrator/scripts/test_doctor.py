#!/usr/bin/env python3
"""Regression tests for scripts/doctor.py."""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("doctor.py")
SPEC = importlib.util.spec_from_file_location("agent_project_doctor", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT}")
DOCTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DOCTOR
SPEC.loader.exec_module(DOCTOR)


SCENARIOS = {
    "schema_version": 1,
    "policy_floor": {"terminal_verification": "required"},
    "scenarios": [
        {
            "id": "claude-code-opus-4.8",
            "harness": "claude-code",
            "model": {"canonical": "claude-opus-4.8", "aliases": ["opus-4.8"]},
            "supported_profiles": ["standard", "autonomous"],
            "scenario_reference": "references/scenario-claude-code-opus-4.8.md",
            "orchestration": {
                "capability_selection": "router_preselected",
                "max_repair_attempts": 1,
                "max_parallel_workers": 2,
            },
            "approval_gates": ["project_contract"],
            "review": {"minimum_independence_level": 3},
        },
        {
            "id": "claude-code-sonnet-5",
            "harness": "claude-code",
            "model": {"canonical": "claude-sonnet-5", "aliases": ["sonnet-5"]},
            "supported_profiles": ["standard", "autonomous"],
            "scenario_reference": "references/scenario-claude-code-sonnet-5.md",
            "orchestration": {
                "capability_selection": "router_preselected_with_recorded_skips",
                "max_repair_attempts": 2,
                "max_parallel_workers": 3,
            },
            "approval_gates": ["project_contract"],
            "review": {"minimum_independence_level": 3},
        },
        {
            "id": "codex-gpt-5.6-sol",
            "harness": "codex",
            "model": {"canonical": "gpt-5.6-sol", "aliases": ["sol-5.6"]},
            "supported_profiles": ["standard", "autonomous"],
            "scenario_reference": "references/scenario-codex-gpt-5.6-sol.md",
            "orchestration": {
                "capability_selection": "adaptive_within_approved_graph",
                "max_repair_attempts": 2,
                "max_parallel_workers": 3,
            },
            "approval_gates": ["project_contract"],
            "review": {"minimum_independence_level": 3},
        },
    ],
}


def write_minimal_package(root: Path) -> None:
    for relative in DOCTOR.REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")
    (root / "SKILL.md").write_text(
        "---\n"
        "name: agent-project-orchestrator\n"
        "description: \"design durable scenario-aware agent project orchestration with backlog, memory, evidence, provider qc, and terminal verification for long-running work.\"\n"
        "---\n\nRead `references/00-reading-guide.md`.\n",
        encoding="utf-8",
    )
    for scenario in SCENARIOS["scenarios"]:
        (root / str(scenario["scenario_reference"])).write_text("scenario\n", encoding="utf-8")
    (root / "references/scenario-profiles.json").write_text(json.dumps(SCENARIOS), encoding="utf-8")
    (root / "references/provider-bindings.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "capabilities": [
                    {
                        "name": "repository_mapping",
                        "required_profiles": ["standard"],
                        "providers": [
                            {
                                "id": "test.repo-map-codex",
                                "harnesses": ["codex"],
                                "invocation_mode": "model",
                                "entrypoint_candidates": ["repo-map-codex/SKILL.md"],
                            },
                            {
                                "id": "test.repo-map-claude",
                                "harnesses": ["claude-code"],
                                "invocation_mode": "model",
                                "entrypoint_candidates": ["repo-map-claude/SKILL.md"],
                            },
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_valid_package_warns_without_provider_roots() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_minimal_package(root)
        findings = DOCTOR.run(root, [], False, "standard")
        assert not [item for item in findings if item.level == "ERROR"], findings
        assert any(item.code == "scenario-profiles" for item in findings), findings


def test_strict_scenario_accepts_matching_provider() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "package"
        skills = Path(temp) / "skills"
        root.mkdir()
        (skills / "repo-map-codex").mkdir(parents=True)
        (skills / "repo-map-codex/SKILL.md").write_text("---\nname: repo-map\ndescription: test\n---\n")
        write_minimal_package(root)
        findings = DOCTOR.run(root, [skills], True, "standard", "codex-gpt-5.6-sol")
        assert not [item for item in findings if item.level == "ERROR"], findings


def test_wrong_harness_provider_does_not_satisfy_scenario() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "package"
        skills = Path(temp) / "skills"
        root.mkdir()
        (skills / "repo-map-claude").mkdir(parents=True)
        (skills / "repo-map-claude/SKILL.md").write_text("---\nname: repo-map\ndescription: test\n---\n")
        write_minimal_package(root)
        findings = DOCTOR.run(root, [skills], True, "standard", "codex-gpt-5.6-sol")
        assert any(item.code == "required-provider-missing" for item in findings), findings


def test_duplicate_scenario_alias_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_minimal_package(root)
        data = json.loads((root / "references/scenario-profiles.json").read_text())
        data["scenarios"][1]["model"]["aliases"].append("opus-4.8")
        (root / "references/scenario-profiles.json").write_text(json.dumps(data))
        findings, _ = DOCTOR.check_scenario_profiles(root)
        assert any(item.code == "duplicate-scenario-alias" for item in findings), findings


def test_unknown_scenario_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_minimal_package(root)
        findings = DOCTOR.run(root, [], False, "standard", "hermes-glm")
        assert any(item.code == "unknown-scenario" for item in findings), findings


def main() -> int:
    tests = [
        test_valid_package_warns_without_provider_roots,
        test_strict_scenario_accepts_matching_provider,
        test_wrong_harness_provider_does_not_satisfy_scenario,
        test_duplicate_scenario_alias_is_rejected,
        test_unknown_scenario_is_rejected,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} doctor regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
