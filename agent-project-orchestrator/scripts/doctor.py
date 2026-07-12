#!/usr/bin/env python3
"""Validate the Agent Project Orchestrator package and declared providers.

This is a package-level doctor for the design-stage skill. It does not certify
or implement the future projectctl transactional runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REQUIRED_FILES = (
    "SKILL.md",
    "README.md",
    "PROVENANCE.md",
    "agents/openai.yaml",
    "references/00-reading-guide.md",
    "references/01-original-scaffold.md",
    "references/original/claude_code_deep_planning.txt",
    "references/02-lineage-and-observed-context.md",
    "references/03-generalized-operating-model.md",
    "references/04-zenith-comparison.md",
    "references/05-adversarial-architecture-review.md",
    "references/06-final-architecture.md",
    "references/07-qc-and-smoke-testing.md",
    "references/08-implementation-roadmap.md",
    "references/09-sources-and-provenance.md",
    "references/provider-bindings.json",
)

FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
REFERENCE_LINK_RE = re.compile(r"`(references/[^`]+)`|\]\((references/[^)]+)\)")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_required_files(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file():
            findings.append(Finding("ERROR", "missing-file", relative))
        elif path.stat().st_size == 0:
            findings.append(Finding("ERROR", "empty-file", relative))
    return findings


def parse_frontmatter(skill_text: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(skill_text)
    if not match:
        raise ValueError("SKILL.md must begin with YAML frontmatter")

    values: dict[str, str] = {}
    for raw_line in match.group("body").splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        if ":" not in raw_line:
            raise ValueError(f"unsupported frontmatter line: {raw_line!r}")
        key, value = raw_line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def check_skill_metadata(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    path = root / "SKILL.md"
    if not path.is_file():
        return findings

    try:
        values = parse_frontmatter(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        return [Finding("ERROR", "frontmatter", str(exc))]

    allowed = {"name", "description"}
    extra = sorted(set(values) - allowed)
    missing = sorted(allowed - set(values))
    if missing:
        findings.append(Finding("ERROR", "frontmatter-missing", ", ".join(missing)))
    if extra:
        findings.append(Finding("ERROR", "frontmatter-extra", ", ".join(extra)))
    if values.get("name") != "agent-project-orchestrator":
        findings.append(Finding("ERROR", "skill-name", "name must be agent-project-orchestrator"))
    description = values.get("description", "")
    if len(description) < 80:
        findings.append(Finding("ERROR", "description-short", "description must explain scope and triggers"))
    return findings


def check_reference_links(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        return findings
    text = skill_path.read_text(encoding="utf-8")
    for match in REFERENCE_LINK_RE.finditer(text):
        relative = match.group(1) or match.group(2)
        if relative and not (root / relative).is_file():
            findings.append(Finding("ERROR", "broken-reference", relative))
    return findings


def normalize_bindings(data: object) -> list[dict[str, object]]:
    if not isinstance(data, dict):
        raise ValueError("provider-bindings.json must contain an object")
    if data.get("schema_version") != 1:
        raise ValueError("unsupported provider binding schema_version")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("capabilities must be a non-empty list")
    normalized: list[dict[str, object]] = []
    for capability in capabilities:
        if not isinstance(capability, dict):
            raise ValueError("each capability must be an object")
        name = capability.get("name")
        providers = capability.get("providers")
        profiles = capability.get("required_profiles", [])
        if not isinstance(name, str) or not name:
            raise ValueError("capability name must be a non-empty string")
        if not isinstance(providers, list) or not providers:
            raise ValueError(f"{name}: providers must be a non-empty list")
        if not isinstance(profiles, list) or not all(isinstance(item, str) for item in profiles):
            raise ValueError(f"{name}: required_profiles must be a string list")
        normalized.append(capability)
    return normalized


def check_provider_bindings(root: Path) -> tuple[list[Finding], list[dict[str, object]]]:
    path = root / "references/provider-bindings.json"
    if not path.is_file():
        return [], []

    try:
        capabilities = normalize_bindings(load_json(path))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [Finding("ERROR", "provider-bindings", str(exc))], []

    findings: list[Finding] = []
    names: set[str] = set()
    provider_ids: set[str] = set()
    valid_modes = {"model", "user", "user-or-model-adapter", "native-tool", "prompt-adapter", "runtime"}

    for capability in capabilities:
        name = str(capability["name"])
        if name in names:
            findings.append(Finding("ERROR", "duplicate-capability", name))
        names.add(name)

        providers = capability["providers"]
        assert isinstance(providers, list)
        for provider in providers:
            if not isinstance(provider, dict):
                findings.append(Finding("ERROR", "provider-shape", name))
                continue
            provider_id = provider.get("id")
            if not isinstance(provider_id, str) or not provider_id:
                findings.append(Finding("ERROR", "provider-id", name))
                continue
            scoped_id = f"{name}:{provider_id}"
            if scoped_id in provider_ids:
                findings.append(Finding("ERROR", "duplicate-provider", scoped_id))
            provider_ids.add(scoped_id)
            mode = provider.get("invocation_mode")
            if mode not in valid_modes:
                findings.append(Finding("ERROR", "invocation-mode", f"{provider_id}: {mode!r}"))
            harnesses = provider.get("harnesses")
            if not isinstance(harnesses, list) or not harnesses:
                findings.append(Finding("ERROR", "provider-harnesses", provider_id))
            candidates = provider.get("entrypoint_candidates", [])
            if not isinstance(candidates, list) or not all(isinstance(item, str) for item in candidates):
                findings.append(Finding("ERROR", "entrypoint-candidates", provider_id))

    return findings, capabilities


def discover_entrypoint(candidate: str, roots: Iterable[Path]) -> Path | None:
    for root in roots:
        direct = root / candidate
        if direct.is_file():
            return direct
        matches = list(root.glob(f"**/{candidate}"))
        if matches:
            return matches[0]
    return None


def check_provider_discovery(capabilities: list[dict[str, object]], roots: list[Path], strict: bool, profile: str) -> list[Finding]:
    findings: list[Finding] = []
    if not roots:
        level = "ERROR" if strict else "WARN"
        findings.append(Finding(level, "provider-roots", "no --skills-root supplied; providers not discovered"))
        return findings

    for capability in capabilities:
        name = str(capability["name"])
        profiles = capability.get("required_profiles", [])
        required = isinstance(profiles, list) and profile in profiles
        providers = capability["providers"]
        assert isinstance(providers, list)
        resolved: list[str] = []
        unverifiable_core: list[str] = []

        for provider in providers:
            assert isinstance(provider, dict)
            provider_id = str(provider.get("id"))
            candidates = provider.get("entrypoint_candidates", [])
            assert isinstance(candidates, list)
            if not candidates:
                unverifiable_core.append(provider_id)
                continue
            for candidate in candidates:
                found = discover_entrypoint(str(candidate), roots)
                if found:
                    resolved.append(f"{provider_id} -> {found}")
                    break

        if resolved:
            findings.append(Finding("PASS", "provider-resolved", f"{name}: {resolved[0]}"))
        elif required and strict:
            detail = ""
            if unverifiable_core:
                detail = f"; declarations without entrypoint: {', '.join(unverifiable_core)}"
            findings.append(Finding("ERROR", "required-provider-missing", f"{name}{detail}"))
        else:
            findings.append(Finding("WARN", "provider-unresolved", f"{name}: no declared entrypoint found"))
    return findings


def run(root: Path, skill_roots: list[Path], strict: bool, profile: str) -> list[Finding]:
    findings: list[Finding] = []
    findings.extend(check_required_files(root))
    findings.extend(check_skill_metadata(root))
    findings.extend(check_reference_links(root))
    binding_findings, capabilities = check_provider_bindings(root)
    findings.extend(binding_findings)
    if capabilities:
        findings.extend(check_provider_discovery(capabilities, skill_roots, strict, profile))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=package_root(), help="package root; defaults to the parent of scripts/")
    parser.add_argument("--skills-root", action="append", default=[], type=Path, help="installed skill root to inspect; may be supplied multiple times")
    parser.add_argument("--profile", choices=("standard", "autonomous"), default="standard")
    parser.add_argument("--strict", action="store_true", help="fail when a required capability has no discoverable provider")
    args = parser.parse_args()

    root = args.root.resolve()
    skill_roots = [path.resolve() for path in args.skills_root]
    findings = run(root, skill_roots, args.strict, args.profile)

    for finding in findings:
        print(f"{finding.level}: {finding.code}: {finding.message}")

    errors = [finding for finding in findings if finding.level == "ERROR"]
    if errors:
        print(f"BLOCKED: {len(errors)} error(s)", file=sys.stderr)
        return 1

    warnings = [finding for finding in findings if finding.level == "WARN"]
    if warnings:
        print(f"READY_WITH_DEGRADATION: {len(warnings)} warning(s)")
    else:
        print("READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
