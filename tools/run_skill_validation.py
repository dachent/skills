from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "skills-manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_skill(manifest_path: Path, name: str) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for skill in manifest.get("skills", []):
        if skill.get("name") == name:
            return skill
    raise ValueError(f"skill is not registered: {name}")


def normalize_command(command: str) -> str:
    return command.replace(".\\", "./").replace("\\", "/")


def command_argv(command: str, repo_root: Path) -> list[str]:
    tokens = shlex.split(normalize_command(command), posix=True)
    expanded: list[str] = []
    for token in tokens:
        if any(mark in token for mark in ("*", "?", "[")):
            matches = sorted(glob.glob(str(repo_root / token)))
            if matches:
                expanded.extend(matches)
                continue
        expanded.append(token)
    return expanded


def validate_structure(skill: dict[str, Any], repo_root: Path) -> list[str]:
    errors: list[str] = []
    skill_path = repo_root / skill.get("path", "")
    if not skill_path.is_dir():
        errors.append(f"missing skill directory: {skill_path}")
    packaging = skill.get("packaging", {})
    for key in ("skill_file", "agent_metadata"):
        value = packaging.get(key)
        if not isinstance(value, str) or not (repo_root / value).is_file():
            errors.append(f"missing packaging.{key}: {value!r}")
    validation = skill.get("validation")
    if not isinstance(validation, dict):
        errors.append("validation must be an object")
    return errors


def run_command(command: str, repo_root: Path) -> dict[str, Any]:
    argv = command_argv(command, repo_root)
    started = time.monotonic()
    try:
        completed = subprocess.run(
            argv,
            cwd=repo_root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        exit_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except OSError as exc:
        exit_code = 127
        stdout = ""
        stderr = str(exc)
    return {
        "command": command,
        "argv": argv,
        "exit_code": exit_code,
        "duration_seconds": round(time.monotonic() - started, 3),
        "stdout": stdout,
        "stderr": stderr,
    }


def build_result(
    skill: dict[str, Any],
    *,
    authority: str,
    structural_only: bool,
    repo_root: Path,
) -> dict[str, Any]:
    started_at = utc_now()
    structural_errors = validate_structure(skill, repo_root)
    commands: list[dict[str, Any]] = []
    if not structural_errors and not structural_only:
        for command in skill.get("validation", {}).get("hosted_commands", []):
            result = run_command(command, repo_root)
            commands.append(result)
            if result["exit_code"] != 0:
                break
    status = "passed"
    if structural_errors or any(item["exit_code"] != 0 for item in commands):
        status = "failed"
    elif structural_only:
        status = "delegated"
    return {
        "schema_version": 1,
        "skill": skill["name"],
        "status": status,
        "authority": authority,
        "structural_only": structural_only,
        "runner": {
            "os": platform.system().lower(),
            "platform": sys.platform,
            "machine": platform.machine(),
            "name": os.environ.get("RUNNER_NAME"),
        },
        "git": {
            "sha": os.environ.get("GITHUB_SHA"),
            "ref": os.environ.get("GITHUB_REF"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
        },
        "started_at": started_at,
        "completed_at": utc_now(),
        "structural_errors": structural_errors,
        "commands": commands,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one skill's hosted validation and emit JSON.")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--authority", default="manifest")
    parser.add_argument("--structural-only", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        skill = load_skill(args.manifest, args.skill)
        result = build_result(
            skill,
            authority=args.authority,
            structural_only=args.structural_only,
            repo_root=args.repo_root.resolve(),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for command in result["commands"]:
        if command["stdout"]:
            print(command["stdout"], end="")
        if command["stderr"]:
            print(command["stderr"], end="", file=sys.stderr)
    if result["structural_errors"]:
        for error in result["structural_errors"]:
            print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result["status"] in {"passed", "delegated"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
