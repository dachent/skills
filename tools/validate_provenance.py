from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / ".upstream" / "anthropic-skills.lock.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def add_failure(failures: list[str], message: str) -> None:
    failures.append(message)


def require_text(mapping: dict, key: str, context: str, failures: list[str]) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        add_failure(failures, f"{context}: missing non-empty string field '{key}'.")
        return ""
    return value


def require_contains(text: str, expected: str, context: str, failures: list[str]) -> None:
    if expected not in text:
        add_failure(failures, f"{context}: expected text not found: {expected}")


def validate_provenance_doc(
    skill_name: str,
    skill: dict,
    upstream_commit: str,
    failures: list[str],
) -> None:
    local_path = skill["local_path"]
    provenance_path = REPO_ROOT / local_path / "PROVENANCE.md"
    context = f"{local_path}/PROVENANCE.md"

    if not provenance_path.is_file():
        add_failure(failures, f"{skill_name}: missing provenance file: {context}")
        return

    text = provenance_path.read_text(encoding="utf-8")
    required_sections = [
        "# Provenance",
        "## Source",
        "## Port Classification",
        "## Design Upskill Contribution",
        "## COM Boundary",
        "## Intentional Divergences",
        "## Last Alignment Review",
    ]
    for section in required_sections:
        require_contains(text, section, context, failures)

    require_contains(text, "https://github.com/anthropics/skills", context, failures)
    require_contains(text, skill["upstream_path"], context, failures)
    require_contains(text, upstream_commit, context, failures)
    require_contains(text, skill["port_depth"], context, failures)
    require_contains(text, "License reviewed:", context, failures)
    require_contains(text, "Design Upskill Contribution", context, failures)


def validate_lock(lock: dict, failures: list[str]) -> None:
    if lock.get("schema_version") != 1:
        add_failure(failures, "lock: schema_version must be 1.")

    upstreams = lock.get("upstreams")
    if not isinstance(upstreams, dict) or "anthropic-skills" not in upstreams:
        add_failure(failures, "lock: missing upstreams.anthropic-skills.")
        return

    anthropic = upstreams["anthropic-skills"]
    if not isinstance(anthropic, dict):
        add_failure(failures, "lock: upstreams.anthropic-skills must be an object.")
        return

    repo = require_text(anthropic, "repo", "upstreams.anthropic-skills", failures)
    if repo and repo != "https://github.com/anthropics/skills":
        add_failure(failures, "upstreams.anthropic-skills: repo must be https://github.com/anthropics/skills.")
    commit = require_text(anthropic, "commit", "upstreams.anthropic-skills", failures)
    if commit and not SHA_RE.match(commit):
        add_failure(failures, "upstreams.anthropic-skills: commit must be a 40-character lowercase hex SHA.")
    require_text(anthropic, "branch_at_fetch", "upstreams.anthropic-skills", failures)
    require_text(anthropic, "fetched_at", "upstreams.anthropic-skills", failures)
    require_text(anthropic, "license_note", "upstreams.anthropic-skills", failures)

    skills = lock.get("skills")
    if not isinstance(skills, dict) or not skills:
        add_failure(failures, "lock: skills must be a non-empty object.")
        return

    for skill_name, skill in sorted(skills.items()):
        context = f"skills.{skill_name}"
        if not isinstance(skill, dict):
            add_failure(failures, f"{context}: must be an object.")
            continue
        source = require_text(skill, "source", context, failures)
        upstream_path = require_text(skill, "upstream_path", context, failures)
        local_path = require_text(skill, "local_path", context, failures)
        require_text(skill, "port_depth", context, failures)
        require_text(skill, "alignment_owner", context, failures)

        if source == "anthropic-skills" and skill.get("snapshot") is not True:
            add_failure(failures, f"{context}: Anthropic-derived active skills must set snapshot true.")

        if local_path:
            local_dir = REPO_ROOT / local_path
            if not local_dir.is_dir():
                add_failure(failures, f"{context}: local_path does not exist: {local_path}")

        if commit and upstream_path:
            snapshot_dir = REPO_ROOT / ".upstream" / "anthropic-skills" / commit / upstream_path
            if skill.get("snapshot") is True and not snapshot_dir.is_dir():
                add_failure(failures, f"{context}: required snapshot is missing at {snapshot_dir.relative_to(REPO_ROOT)}")
            elif skill.get("snapshot") is True:
                license_path = snapshot_dir / "LICENSE.txt"
                if not license_path.is_file():
                    add_failure(failures, f"{context}: snapshot is missing upstream LICENSE.txt at {license_path.relative_to(REPO_ROOT)}")

        if commit:
            validate_provenance_doc(skill_name, skill, commit, failures)


def main() -> int:
    failures: list[str] = []

    if not LOCK_PATH.is_file():
        add_failure(failures, f"missing lock file: {LOCK_PATH.relative_to(REPO_ROOT)}")
    else:
        try:
            lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            add_failure(failures, f"lock JSON is invalid: {exc}")
        else:
            validate_lock(lock, failures)

    if failures:
        for item in failures:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1

    print("Provenance validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
