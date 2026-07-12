from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "skills-manifest.json"
RUNNERS_BY_PLATFORM = {
    "cross-platform": ("ubuntu-latest", "windows-latest", "macos-latest"),
    "linux": ("ubuntu-latest",),
    "windows": ("windows-latest",),
    "macos": ("macos-latest",),
}
SPECIALIZED_WORKFLOWS = {
    "code-mapper-skill": ".github/workflows/code-mapper-codeql.yml",
}
FULL_VALIDATION_PATHS = {
    "skills-manifest.json",
    "tools/ci_matrix.py",
    "tools/run_skill_validation.py",
    "tools/write_test_result.py",
    "tools/repository_health.py",
    "tools/validate_actions.py",
    ".github/workflows/validate.yml",
}
FULL_VALIDATION_PREFIXES = (
    ".github/actions/",
    ".generated/",
)


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("skills"), list):
        raise ValueError("manifest must be an object containing a skills list")
    return data


def normalize_path(value: str) -> str:
    return value.strip().replace("\\", "/").lstrip("./")


def supported_skills(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    return [skill for skill in manifest["skills"] if skill.get("status") == "supported"]


def skill_map(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {skill["name"]: skill for skill in supported_skills(manifest)}


def _matches_path(changed: str, declared: str) -> bool:
    changed = normalize_path(changed)
    declared = normalize_path(declared).rstrip("/")
    return changed == declared or changed.startswith(declared + "/")


def affected_skill_names(
    manifest: dict[str, Any],
    changed_files: Iterable[str],
    *,
    full: bool = False,
) -> list[str]:
    skills = supported_skills(manifest)
    names = {skill["name"] for skill in skills}
    if full:
        return sorted(names)

    changed = {normalize_path(path) for path in changed_files if path.strip()}
    if not changed:
        return []
    if changed & FULL_VALIDATION_PATHS or any(
        any(_matches_path(path, prefix) for prefix in FULL_VALIDATION_PREFIXES)
        for path in changed
    ):
        return sorted(names)

    affected: set[str] = set()
    for skill in skills:
        if any(_matches_path(path, skill["path"]) for path in changed):
            affected.add(skill["name"])
        packaging = skill.get("packaging", {})
        for value in packaging.values():
            if isinstance(value, str) and any(_matches_path(path, value) for path in changed):
                affected.add(skill["name"])

    for component in manifest.get("shared_components", []):
        component_path = component.get("path")
        if isinstance(component_path, str) and any(
            _matches_path(path, component_path) for path in changed
        ):
            affected.update(component.get("consumers", []))

    for mirror in manifest.get("generated_mirrors", []):
        source = mirror.get("source")
        destination = mirror.get("destination")
        if any(
            isinstance(candidate, str)
            and any(_matches_path(path, candidate) for path in changed)
            for candidate in (source, destination)
        ):
            for skill in skills:
                if isinstance(source, str) and _matches_path(source, skill["path"]):
                    affected.add(skill["name"])

    return sorted(affected & names)


def runners_for_skill(skill: dict[str, Any]) -> list[str]:
    runners: set[str] = set()
    unknown: list[str] = []
    for platform in skill.get("platforms", []):
        mapped = RUNNERS_BY_PLATFORM.get(platform)
        if mapped is None:
            unknown.append(platform)
        else:
            runners.update(mapped)
    if unknown:
        raise ValueError(
            f"{skill.get('name', '<unknown>')}: unsupported CI platforms: {', '.join(unknown)}"
        )
    if not runners:
        raise ValueError(f"{skill.get('name', '<unknown>')}: no approved CI runner")
    order = {"ubuntu-latest": 0, "windows-latest": 1, "macos-latest": 2}
    return sorted(runners, key=order.__getitem__)


def build_matrix(
    manifest: dict[str, Any],
    selected_names: Iterable[str],
) -> dict[str, list[dict[str, Any]]]:
    by_name = skill_map(manifest)
    include: list[dict[str, Any]] = []
    for name in sorted(set(selected_names)):
        skill = by_name.get(name)
        if skill is None:
            raise ValueError(f"unknown supported skill: {name}")
        authority = SPECIALIZED_WORKFLOWS.get(name, "manifest")
        for runner in runners_for_skill(skill):
            include.append(
                {
                    "skill": name,
                    "runner": runner,
                    "authority": authority,
                    "structural_only": authority != "manifest",
                }
            )
    return {"include": include}


def build_plan(
    manifest: dict[str, Any],
    changed_files: Iterable[str],
    *,
    full: bool = False,
) -> dict[str, Any]:
    selected = affected_skill_names(manifest, changed_files, full=full)
    matrix = build_matrix(manifest, selected)
    specialized = sorted(name for name in selected if name in SPECIALIZED_WORKFLOWS)
    return {
        "schema_version": 1,
        "mode": "full" if full else "affected",
        "selected_skills": selected,
        "matrix": matrix,
        "has_jobs": bool(matrix["include"]),
        "specialized_skills": specialized,
        "specialized_workflows": {
            name: SPECIALIZED_WORKFLOWS[name] for name in specialized
        },
    }


def write_github_output(path: Path, plan: dict[str, Any]) -> None:
    values = {
        "matrix": json.dumps(plan["matrix"], separators=(",", ":")),
        "has_jobs": str(plan["has_jobs"]).lower(),
        "specialized": json.dumps(plan["specialized_skills"], separators=(",", ":")),
        "selected": json.dumps(plan["selected_skills"], separators=(",", ":")),
    }
    with path.open("a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def read_changed_files(path: Path | None, inline: list[str]) -> list[str]:
    values = list(inline)
    if path is not None:
        values.extend(path.read_text(encoding="utf-8").splitlines())
    return [item for item in values if item.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build manifest-driven GitHub Actions matrices.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--changed-files", type=Path)
    parser.add_argument("--full", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.manifest)
        changed = read_changed_files(args.changed_files, args.changed_file)
        plan = build_plan(manifest, changed, full=args.full)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    rendered = json.dumps(plan, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    if args.github_output:
        write_github_output(args.github_output, plan)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
