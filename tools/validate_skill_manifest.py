from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
FRONT_MATTER_RE = re.compile(r"^---\r?\n(?P<body>[\s\S]*?)\r?\n---")
FIELD_RE = re.compile(r"^(?P<key>[A-Za-z0-9_-]+):\s*(?P<value>.*)$")


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def load_json(path: Path, errors: list[str]) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(errors, f"missing manifest: {path}")
        return {}
    except json.JSONDecodeError as exc:
        fail(errors, f"invalid manifest JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        fail(errors, "manifest root must be an object")
        return {}
    return value


def parse_flat_yaml(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped == "---" or stripped.startswith("#"):
            continue
        match = FIELD_RE.match(stripped)
        if not match:
            continue
        value = match.group("value").strip().strip('"\'')
        values[match.group("key")] = value
    return values


def discover_skill_paths(repo_root: Path) -> set[str]:
    found: set[str] = set()
    for child in repo_root.iterdir():
        if not child.is_dir() or child.name.startswith("."):
            continue
        if (child / "SKILL.md").is_file():
            found.add(child.name)
    return found


def validate_date(value: Any, context: str, errors: list[str]) -> None:
    if not isinstance(value, str):
        fail(errors, f"{context}: last_reviewed must be YYYY-MM-DD")
        return
    try:
        dt.date.fromisoformat(value)
    except ValueError:
        fail(errors, f"{context}: invalid last_reviewed date {value!r}")


def require_string(mapping: dict[str, Any], key: str, context: str, errors: list[str]) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        fail(errors, f"{context}: missing non-empty string {key!r}")
        return ""
    return value


def require_string_list(mapping: dict[str, Any], key: str, context: str, errors: list[str]) -> list[str]:
    value = mapping.get(key)
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x for x in value):
        fail(errors, f"{context}: {key!r} must be a non-empty list of strings")
        return []
    return value


def validate_skill_file(path: Path, expected_name: str, errors: list[str]) -> None:
    if not path.is_file():
        fail(errors, f"{expected_name}: missing skill file {path}")
        return
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        fail(errors, f"{expected_name}: SKILL.md is missing YAML front matter")
        return
    fields = parse_flat_yaml(match.group("body"))
    if fields.get("name") != expected_name:
        fail(errors, f"{expected_name}: SKILL.md name is {fields.get('name')!r}")
    if not fields.get("description"):
        fail(errors, f"{expected_name}: SKILL.md description is missing")


def validate_agent_metadata(path: Path, skill_name: str, errors: list[str]) -> None:
    if not path.is_file():
        fail(errors, f"{skill_name}: missing agent metadata {path}")
        return
    text = path.read_text(encoding="utf-8")
    for token in ("display_name:", "short_description:", "default_prompt:"):
        if token not in text:
            fail(errors, f"{skill_name}: {path} is missing {token[:-1]}")


def validate_manifest(repo_root: Path, manifest_path: Path) -> list[str]:
    errors: list[str] = []
    manifest = load_json(manifest_path, errors)
    if not manifest:
        return errors
    if manifest.get("schema_version") != 1:
        fail(errors, "schema_version must be 1")

    policy = manifest.get("policy")
    if not isinstance(policy, dict):
        fail(errors, "policy must be an object")
        policy = {}
    valid_statuses = set(policy.get("supported_statuses", []))
    valid_sources = set(policy.get("source_classifications", []))
    catalog_groups = policy.get("catalog_groups", [])
    if not isinstance(catalog_groups, list) or not catalog_groups:
        fail(errors, "policy.catalog_groups must be a non-empty list")
        catalog_groups = []
    catalog_group_keys = set()
    for index, group in enumerate(catalog_groups):
        context = f"policy.catalog_groups[{index}]"
        if not isinstance(group, dict):
            fail(errors, f"{context}: must be an object")
            continue
        key = require_string(group, "key", context, errors)
        require_string(group, "title", context, errors)
        require_string(group, "description", context, errors)
        if key in catalog_group_keys:
            fail(errors, f"duplicate catalog group: {key}")
        catalog_group_keys.add(key)
    required_packaging = policy.get("required_packaging_for_supported", [])
    if not valid_statuses or not valid_sources:
        fail(errors, "policy status and source classification lists must be non-empty")
    if not isinstance(required_packaging, list):
        fail(errors, "required_packaging_for_supported must be a list")
        required_packaging = []

    skills = manifest.get("skills")
    if not isinstance(skills, list) or not skills:
        fail(errors, "skills must be a non-empty list")
        return errors

    names: set[str] = set()
    paths: set[str] = set()
    declared_existing_paths: set[str] = set()
    for index, raw in enumerate(skills):
        context = f"skills[{index}]"
        if not isinstance(raw, dict):
            fail(errors, f"{context}: must be an object")
            continue
        name = require_string(raw, "name", context, errors)
        path_value = require_string(raw, "path", context, errors)
        if name in names:
            fail(errors, f"duplicate skill name: {name}")
        names.add(name)
        if path_value in paths:
            fail(errors, f"duplicate skill path: {path_value}")
        paths.add(path_value)
        if path_value and ("/" in path_value or "\\" in path_value or path_value.startswith(".")):
            fail(errors, f"{name}: skill path must be one top-level directory")

        status = require_string(raw, "status", name or context, errors)
        if status and status not in valid_statuses:
            fail(errors, f"{name}: unsupported status {status!r}")
        require_string(raw, "family", name or context, errors)
        catalog_group = require_string(raw, "catalog_group", name or context, errors)
        if catalog_group and catalog_group not in catalog_group_keys:
            fail(errors, f"{name}: unknown catalog_group {catalog_group!r}")
        require_string(raw, "description", name or context, errors)
        require_string(raw, "owner", name or context, errors)
        require_string_list(raw, "platforms", name or context, errors)
        require_string_list(raw, "agents", name or context, errors)
        validate_date(raw.get("last_reviewed"), name or context, errors)

        packaging = raw.get("packaging")
        if not isinstance(packaging, dict):
            fail(errors, f"{name}: packaging must be an object")
            packaging = {}
        if status == "supported":
            for field in required_packaging:
                if not isinstance(packaging.get(field), str) or not packaging[field]:
                    fail(errors, f"{name}: supported skill is missing packaging.{field}")
        skill_file_rel = packaging.get("skill_file")
        metadata_rel = packaging.get("agent_metadata")
        provenance_rel = packaging.get("provenance_file")
        if isinstance(skill_file_rel, str):
            validate_skill_file(repo_root / skill_file_rel, name, errors)
        if isinstance(metadata_rel, str):
            validate_agent_metadata(repo_root / metadata_rel, name, errors)
        if isinstance(provenance_rel, str) and not (repo_root / provenance_rel).is_file():
            fail(errors, f"{name}: missing provenance file {provenance_rel}")

        source = raw.get("source")
        if not isinstance(source, dict):
            fail(errors, f"{name}: source must be an object")
            source = {}
        classification = require_string(source, "classification", f"{name}.source", errors)
        if classification and classification not in valid_sources:
            fail(errors, f"{name}: unsupported source classification {classification!r}")
        if classification not in {"repo-owned-original", "local-source-import"}:
            require_string(source, "repository", f"{name}.source", errors)
            require_string(source, "path", f"{name}.source", errors)
            revision = source.get("revision")
            provenance_status = source.get("provenance_status")
            if revision is None:
                if provenance_status != "revision-unresolved":
                    fail(errors, f"{name}.source: missing revision or explicit revision-unresolved provenance status")
            elif not isinstance(revision, str) or not SHA_RE.fullmatch(revision):
                fail(errors, f"{name}: source revision must be a 40-character lowercase SHA")
        elif classification == "local-source-import":
            initial_commit = require_string(source, "initial_commit", f"{name}.source", errors)
            if initial_commit and not SHA_RE.fullmatch(initial_commit):
                fail(errors, f"{name}: initial_commit must be a 40-character lowercase SHA")

        validation = raw.get("validation")
        if not isinstance(validation, dict):
            fail(errors, f"{name}: validation must be an object")
        else:
            for key in ("hosted_commands", "environment_dependent_commands"):
                value = validation.get(key)
                if not isinstance(value, list) or any(not isinstance(x, str) or not x for x in value):
                    fail(errors, f"{name}: validation.{key} must be a list of strings")
        if path_value and status != "archived":
            declared_existing_paths.add(path_value)

    discovered = discover_skill_paths(repo_root)
    for item in sorted(discovered - declared_existing_paths):
        fail(errors, f"unregistered top-level skill directory: {item}")
    for item in sorted(declared_existing_paths - discovered):
        fail(errors, f"manifest skill directory is missing or lacks SKILL.md: {item}")


    mirrors = manifest.get("generated_mirrors", [])
    if not isinstance(mirrors, list):
        fail(errors, "generated_mirrors must be a list")
    else:
        destinations: set[str] = set()
        for index, mirror in enumerate(mirrors):
            context = f"generated_mirrors[{index}]"
            if not isinstance(mirror, dict):
                fail(errors, f"{context}: must be an object")
                continue
            source_path = require_string(mirror, "source", context, errors)
            destination = require_string(mirror, "destination", context, errors)
            transform = require_string(mirror, "transform", context, errors)
            if source_path and not (repo_root / source_path).is_file():
                fail(errors, f"{context}: missing source {source_path}")
            normalized = destination.replace("\\", "/")
            if destination and not normalized.startswith(".claude/skills/"):
                fail(errors, f"{context}: destination must be under .claude/skills")
            if destination in destinations:
                fail(errors, f"duplicate generated mirror destination: {destination}")
            destinations.add(destination)
            if transform != "copy-with-generated-notice":
                fail(errors, f"{context}: unsupported transform {transform!r}")

    shared = manifest.get("shared_components", [])
    if not isinstance(shared, list):
        fail(errors, "shared_components must be a list")
    else:
        for index, component in enumerate(shared):
            context = f"shared_components[{index}]"
            if not isinstance(component, dict):
                fail(errors, f"{context}: must be an object")
                continue
            path_value = require_string(component, "path", context, errors)
            consumers = require_string_list(component, "consumers", context, errors)
            if path_value and not (repo_root / path_value).is_dir():
                fail(errors, f"{context}: missing path {path_value}")
            unknown = sorted(set(consumers) - names)
            if unknown:
                fail(errors, f"{context}: unknown consumers: {', '.join(unknown)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate skills-manifest.json and repository integration.")
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    manifest_path = args.manifest.resolve() if args.manifest else repo_root / "skills-manifest.json"
    errors = validate_manifest(repo_root, manifest_path)
    if errors:
        for item in errors:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    print(f"Validated {len(data['skills'])} skills and {len(data.get('shared_components', []))} shared components.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
