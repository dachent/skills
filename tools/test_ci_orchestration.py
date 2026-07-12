from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import ci_matrix
import run_skill_validation


class CiMatrixTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = {
            "skills": [
                {
                    "name": "alpha",
                    "path": "alpha",
                    "status": "supported",
                    "platforms": ["cross-platform"],
                    "packaging": {
                        "skill_file": "alpha/SKILL.md",
                        "agent_metadata": "alpha/agents/openai.yaml",
                    },
                    "validation": {
                        "hosted_commands": [],
                        "environment_dependent_commands": [],
                    },
                },
                {
                    "name": "beta",
                    "path": "beta",
                    "status": "supported",
                    "platforms": ["windows"],
                    "packaging": {
                        "skill_file": "beta/SKILL.md",
                        "agent_metadata": "beta/agents/openai.yaml",
                    },
                    "validation": {
                        "hosted_commands": [],
                        "environment_dependent_commands": [],
                    },
                },
                {
                    "name": "experimental-enabled",
                    "path": "experimental-enabled",
                    "status": "experimental",
                    "platforms": ["linux"],
                    "packaging": {
                        "skill_file": "experimental-enabled/SKILL.md",
                        "agent_metadata": "experimental-enabled/agents/openai.yaml",
                    },
                    "validation": {
                        "ci_enabled": True,
                        "hosted_commands": [],
                        "environment_dependent_commands": [],
                    },
                },
                {
                    "name": "experimental-disabled",
                    "path": "experimental-disabled",
                    "status": "experimental",
                    "platforms": ["linux"],
                    "packaging": {},
                    "validation": {
                        "hosted_commands": [],
                        "environment_dependent_commands": [],
                    },
                },
                {
                    "name": "old",
                    "path": "old",
                    "status": "archived",
                    "platforms": ["linux"],
                    "packaging": {},
                    "validation": {
                        "hosted_commands": [],
                        "environment_dependent_commands": [],
                    },
                },
            ],
            "shared_components": [
                {
                    "name": "runtime",
                    "path": ".shared/runtime",
                    "consumers": ["alpha", "beta"],
                }
            ],
            "generated_mirrors": [],
        }

    def test_direct_change_selects_skill(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(self.manifest, ["alpha/SKILL.md"]),
            ["alpha"],
        )

    def test_shared_change_expands_consumers(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(
                self.manifest, [".shared/runtime/helper.py"]
            ),
            ["alpha", "beta"],
        )

    def test_full_includes_opted_in_experimental_and_excludes_others(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(self.manifest, [], full=True),
            ["alpha", "beta", "experimental-enabled"],
        )

    def test_experimental_skill_requires_explicit_ci_opt_in(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(
                self.manifest, ["experimental-disabled/SKILL.md"]
            ),
            [],
        )

    def test_experimental_skill_with_ci_opt_in_is_selected(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(
                self.manifest, ["experimental-enabled/SKILL.md"]
            ),
            ["experimental-enabled"],
        )

    def test_cross_platform_expands_approved_runners(self) -> None:
        plan = ci_matrix.build_plan(self.manifest, ["alpha/SKILL.md"])
        self.assertEqual(
            [item["runner"] for item in plan["matrix"]["include"]],
            ["ubuntu-latest", "windows-latest", "macos-latest"],
        )

    def test_control_file_selects_all_ci_enabled(self) -> None:
        self.assertEqual(
            ci_matrix.affected_skill_names(self.manifest, ["tools/ci_matrix.py"]),
            ["alpha", "beta", "experimental-enabled"],
        )


class SkillRunnerTests(unittest.TestCase):
    def test_runner_writes_delegated_result_for_structural_only_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "alpha/agents").mkdir(parents=True)
            (root / "alpha/SKILL.md").write_text(
                "---\nname: alpha\ndescription: x\n---\n", encoding="utf-8"
            )
            (root / "alpha/agents/openai.yaml").write_text(
                "display_name: Alpha\n", encoding="utf-8"
            )
            skill = {
                "name": "alpha",
                "path": "alpha",
                "packaging": {
                    "skill_file": "alpha/SKILL.md",
                    "agent_metadata": "alpha/agents/openai.yaml",
                },
                "validation": {"hosted_commands": []},
            }
            result = run_skill_validation.build_result(
                skill,
                authority="specialized.yml",
                structural_only=True,
                repo_root=root,
            )
            self.assertEqual(result["status"], "delegated")
            self.assertEqual(result["structural_errors"], [])

    def test_command_normalization(self) -> None:
        normalized = run_skill_validation.normalize_command(
            r"python .\tools\check.py"
        )
        self.assertEqual(normalized, "python ./tools/check.py")


class RepositoryManifestIntegrationTests(unittest.TestCase):
    def test_full_matrix_covers_every_ci_enabled_skill(self) -> None:
        manifest = ci_matrix.load_manifest()
        expected = sorted(
            skill["name"]
            for skill in manifest["skills"]
            if skill.get("status") == "supported"
            or skill.get("validation", {}).get("ci_enabled") is True
        )
        plan = ci_matrix.build_plan(manifest, [], full=True)
        self.assertEqual(plan["selected_skills"], expected)
        covered = {item["skill"] for item in plan["matrix"]["include"]}
        self.assertEqual(covered, set(expected))

    def test_every_shared_component_change_expands_all_consumers(self) -> None:
        manifest = ci_matrix.load_manifest()
        for component in manifest.get("shared_components", []):
            changed = f"{component['path']}/__ci_probe__"
            selected = set(ci_matrix.affected_skill_names(manifest, [changed]))
            self.assertTrue(
                set(component["consumers"]).issubset(selected), component["name"]
            )


if __name__ == "__main__":
    unittest.main()
