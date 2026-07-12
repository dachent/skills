from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from validate_skill_manifest import validate_manifest


class ManifestValidatorTest(unittest.TestCase):
    def make_repo(self, root: Path) -> Path:
        skill = root / "sample-skill"
        (skill / "agents").mkdir(parents=True)
        (skill / "SKILL.md").write_text(
            "---\nname: sample-skill\ndescription: Sample.\n---\n\n# Sample\n",
            encoding="utf-8",
        )
        (skill / "agents" / "openai.yaml").write_text(
            "interface:\n  display_name: Sample\n  short_description: Sample skill\n  default_prompt: Use $sample-skill.\n",
            encoding="utf-8",
        )
        (root / ".shared" / "runtime").mkdir(parents=True)
        manifest = {
            "schema_version": 1,
            "repository": "example/repo",
            "policy": {
                "supported_statuses": ["supported", "archived"],
                "source_classifications": ["repo-owned-original"],
                "required_packaging_for_supported": ["skill_file", "agent_metadata"],
                "catalog_groups": [{"key": "test", "title": "Test", "description": "Test skills."}],
            },
            "generated_mirrors": [],
            "shared_components": [
                {"name": "runtime", "path": ".shared/runtime", "consumers": ["sample-skill"]}
            ],
            "skills": [
                {
                    "name": "sample-skill",
                    "path": "sample-skill",
                    "family": "test",
                    "catalog_group": "test",
                    "status": "supported",
                    "description": "Sample.",
                    "platforms": ["linux"],
                    "agents": ["codex"],
                    "runtimes": {"type": "prompt"},
                    "packaging": {
                        "skill_file": "sample-skill/SKILL.md",
                        "agent_metadata": "sample-skill/agents/openai.yaml",
                    },
                    "source": {"classification": "repo-owned-original"},
                    "validation": {"hosted_commands": [], "environment_dependent_commands": []},
                    "owner": "@owner",
                    "last_reviewed": "2026-07-11",
                }
            ],
        }
        path = root / "skills-manifest.json"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        return path

    def test_valid_repository(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.make_repo(root)
            self.assertEqual(validate_manifest(root, manifest), [])

    def test_unregistered_skill_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.make_repo(root)
            extra = root / "unregistered"
            extra.mkdir()
            (extra / "SKILL.md").write_text(
                "---\nname: unregistered\ndescription: X\n---\n", encoding="utf-8"
            )
            errors = validate_manifest(root, manifest)
            self.assertTrue(any("unregistered top-level skill directory" in item for item in errors))

    def test_missing_metadata_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = self.make_repo(root)
            (root / "sample-skill" / "agents" / "openai.yaml").unlink()
            errors = validate_manifest(root, manifest)
            self.assertTrue(any("missing agent metadata" in item for item in errors))


if __name__ == "__main__":
    unittest.main(verbosity=2)
