from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

REQUIRED_AGENTS = [
    "visual-critic.md",
    "frontend-builder.md",
    "artifact-packager.md",
    "accessibility-reviewer.md",
    "office-com-validator.md",
]

REQUIRED_HOOK_IDS = [
    "visual-qa-evidence-reminder",
    "powerpoint-render-evidence-reminder",
    "provenance-review-reminder",
    "office-com-boundary-reminder",
    "accessibility-check-reminder",
]


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def require_file(relative_path: str, failures: list[str]) -> None:
    if not (REPO_ROOT / relative_path).is_file():
        failures.append(f"missing file: {relative_path}")


def require_contains(text: str, expected: str, context: str, failures: list[str]) -> None:
    if expected not in text:
        failures.append(f"{context}: missing expected text: {expected}")


def validate_agents(failures: list[str]) -> None:
    for filename in REQUIRED_AGENTS:
        relative_path = f".codex/agents/{filename}"
        require_file(relative_path, failures)
        path = REPO_ROOT / relative_path
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for expected in [
            "# ",
            "## Use When",
            "## Inputs",
            "## Output",
            "## Design Upskill Contribution",
            "## COM Boundary",
        ]:
            require_contains(text, expected, relative_path, failures)
        if filename == "office-com-validator.md":
            require_contains(text, "does not instantiate Office", relative_path, failures)
            require_contains(text, "reviews COM logs", relative_path, failures)


def validate_hooks(failures: list[str]) -> None:
    hooks_path = REPO_ROOT / ".codex" / "hooks.json"
    hooks_doc_path = REPO_ROOT / ".codex" / "HOOKS.md"
    require_file(".codex/hooks.json", failures)
    require_file(".codex/HOOKS.md", failures)
    if not hooks_path.is_file():
        return

    try:
        payload = json.loads(hooks_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f".codex/hooks.json: invalid JSON: {exc}")
        return

    if payload.get("schema_version") != 1:
        failures.append(".codex/hooks.json: schema_version must be 1.")
    if payload.get("mode") != "warning-only":
        failures.append(".codex/hooks.json: mode must be warning-only.")

    hooks = payload.get("hooks")
    if not isinstance(hooks, list) or not hooks:
        failures.append(".codex/hooks.json: hooks must be a non-empty list.")
        return

    seen_ids: set[str] = set()
    for hook in hooks:
        if not isinstance(hook, dict):
            failures.append(".codex/hooks.json: each hook must be an object.")
            continue
        hook_id = hook.get("id")
        if not isinstance(hook_id, str) or not hook_id.strip():
            failures.append(".codex/hooks.json: each hook needs a non-empty id.")
            continue
        if hook_id in seen_ids:
            failures.append(f".codex/hooks.json: duplicate hook id {hook_id}.")
        seen_ids.add(hook_id)

        if hook.get("severity") != "warning":
            failures.append(f".codex/hooks.json: {hook_id} severity must be warning.")
        if hook.get("blocking") is not False:
            failures.append(f".codex/hooks.json: {hook_id} blocking must be false.")
        if not isinstance(hook.get("message"), str) or not hook["message"].strip():
            failures.append(f".codex/hooks.json: {hook_id} needs a message.")
        if not isinstance(hook.get("reminder"), str) or not hook["reminder"].strip():
            failures.append(f".codex/hooks.json: {hook_id} needs a reminder.")

    for hook_id in REQUIRED_HOOK_IDS:
        if hook_id not in seen_ids:
            failures.append(f".codex/hooks.json: missing hook id {hook_id}.")

    if hooks_doc_path.is_file():
        hooks_doc = hooks_doc_path.read_text(encoding="utf-8")
        for expected in [
            "warning-only",
            "visual QA",
            "PowerPoint rendering",
            "provenance review",
            "No hook runs Office COM",
        ]:
            require_contains(hooks_doc, expected, ".codex/HOOKS.md", failures)


def validate_readme_and_ci(failures: list[str]) -> None:
    readme = read("README.md")
    workflow = read(".github/workflows/validate.yml")
    for expected in [
        ".codex/agents",
        ".codex/hooks.json",
        "validate_codex_hooks.py",
        "warning-only",
        "visual QA",
    ]:
        require_contains(readme, expected, "README.md", failures)
    require_contains(workflow, "python .\\tools\\validate_codex_hooks.py", ".github/workflows/validate.yml", failures)


def main() -> int:
    failures: list[str] = []
    validate_agents(failures)
    validate_hooks(failures)
    validate_readme_and_ci(failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Codex hooks and agents validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
