#!/usr/bin/env python3
"""Regression tests for scripts/doctor.py."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import sys
from pathlib import Path


SCRIPT = Path(__file__).with_name("doctor.py")
SPEC = importlib.util.spec_from_file_location("agent_project_doctor", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {SCRIPT}")
DOCTOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = DOCTOR
SPEC.loader.exec_module(DOCTOR)


def write_minimal_package(root: Path) -> None:
    for relative in DOCTOR.REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("placeholder\n", encoding="utf-8")

    (root / "SKILL.md").write_text(
        "---\n"
        "name: agent-project-orchestrator\n"
        "description: \"design durable agent project orchestration with backlog, memory, evidence, provider qc, and terminal verification for long-running work.\"\n"
        "---\n\n"
        "Read `references/00-reading-guide.md`.\n",
        encoding="utf-8",
    )
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
                                "id": "test.repo-map",
                                "harnesses": ["codex"],
                                "invocation_mode": "model",
                                "entrypoint_candidates": ["repo-map/SKILL.md"],
                            }
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
        assert any(item.code == "provider-roots" for item in findings), findings


def test_strict_mode_blocks_missing_required_provider() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "package"
        skills = Path(temp) / "skills"
        root.mkdir()
        skills.mkdir()
        write_minimal_package(root)
        findings = DOCTOR.run(root, [skills], True, "standard")
        assert any(item.code == "required-provider-missing" for item in findings), findings


def test_strict_mode_accepts_discovered_provider() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp) / "package"
        skills = Path(temp) / "skills"
        root.mkdir()
        (skills / "repo-map").mkdir(parents=True)
        (skills / "repo-map/SKILL.md").write_text("---\nname: repo-map\ndescription: test\n---\n")
        write_minimal_package(root)
        findings = DOCTOR.run(root, [skills], True, "standard")
        assert not [item for item in findings if item.level == "ERROR"], findings
        assert any(item.code == "provider-resolved" for item in findings), findings


def test_duplicate_capability_is_rejected() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        write_minimal_package(root)
        data = json.loads((root / "references/provider-bindings.json").read_text())
        data["capabilities"].append(data["capabilities"][0])
        (root / "references/provider-bindings.json").write_text(json.dumps(data))
        findings, _ = DOCTOR.check_provider_bindings(root)
        assert any(item.code == "duplicate-capability" for item in findings), findings


def main() -> int:
    tests = [
        test_valid_package_warns_without_provider_roots,
        test_strict_mode_blocks_missing_required_provider,
        test_strict_mode_accepts_discovered_provider,
        test_duplicate_capability_is_rejected,
    ]
    for test in tests:
        test()
    print(f"PASS: {len(tests)} doctor regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
