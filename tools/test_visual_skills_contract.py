from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

VISUAL_SKILLS = {
    "frontend-design-codex": [
        "responsive UI",
        "accessibility",
        "screenshot evidence",
    ],
    "web-artifacts-builder-codex": [
        "standalone web artifact",
        "package evidence",
        "console capture",
    ],
    "theme-factory-codex": [
        "design tokens",
        "palette",
        "typography",
    ],
    "canvas-design-codex": [
        "canvas",
        "pixel",
        "image bounds",
    ],
    "artifact-runtime-codex": [
        "runtime handoff",
        "local server",
        "evidence bundle",
    ],
}


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def normalize_workflow_text(text: str) -> str:
    return text.replace("\\", "/")


def require_file(relative_path: str, failures: list[str]) -> None:
    if not (REPO_ROOT / relative_path).is_file():
        failures.append(f"missing file: {relative_path}")


def require_contains(text: str, expected: str, context: str, failures: list[str]) -> None:
    if expected not in text:
        failures.append(f"{context}: missing expected text: {expected}")


def validate_skill(skill_name: str, required_terms: list[str], failures: list[str]) -> None:
    skill_path = REPO_ROOT / skill_name / "SKILL.md"
    agent_path = REPO_ROOT / skill_name / "agents" / "openai.yaml"
    require_file(f"{skill_name}/SKILL.md", failures)
    require_file(f"{skill_name}/agents/openai.yaml", failures)
    if not skill_path.is_file():
        return

    text = skill_path.read_text(encoding="utf-8")
    for expected in [
        f"name: {skill_name}",
        "description: Use when",
        "## Design Upskill Contribution",
        "## Shared Visual Runtime",
        "## Verification",
        ".shared\\visual-runtime",
        "No Office COM is required",
        "screenshot",
        "visual lint",
    ]:
        require_contains(text, expected, f"{skill_name}/SKILL.md", failures)

    for expected in required_terms:
        require_contains(text, expected, f"{skill_name}/SKILL.md", failures)

    if "New-Object -ComObject" in text or "office_com_preflight" in text:
        failures.append(f"{skill_name}/SKILL.md: visual skills must not instantiate or preflight Office COM.")

    if agent_path.is_file():
        agent_text = agent_path.read_text(encoding="utf-8")
        for expected in ["display_name:", "short_description:", "default_prompt:"]:
            require_contains(agent_text, expected, f"{skill_name}/agents/openai.yaml", failures)


def validate_readme_and_ci(failures: list[str]) -> None:
    readme = read("README.md")
    workflow = normalize_workflow_text(read(".github/workflows/validate.yml"))
    for skill_name in VISUAL_SKILLS:
        require_contains(readme, f"[`{skill_name}`](./{skill_name})", "README.md", failures)
        require_contains(readme, skill_name, "README.md", failures)
    require_contains(readme, "Codex visual skills", "README.md", failures)
    require_contains(readme, "test_visual_skills_contract.py", "README.md", failures)
    require_contains(workflow, "python ./tools/test_visual_skills_contract.py", ".github/workflows/validate.yml", failures)


def main() -> int:
    failures: list[str] = []
    for skill_name, required_terms in VISUAL_SKILLS.items():
        validate_skill(skill_name, required_terms, failures)
    validate_readme_and_ci(failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Visual skills contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
