#!/usr/bin/env python3
"""Validate the three-scenario Agent Project Orchestrator package."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

REQUIRED_FILES = (
    "SKILL.md", "README.md", "PROVENANCE.md", "agents/openai.yaml",
    "references/00-reading-guide.md", "references/01-original-scaffold.md",
    "references/original/claude_code_deep_planning.txt",
    "references/02-lineage-and-observed-context.md",
    "references/03-generalized-operating-model.md",
    "references/04-zenith-comparison.md",
    "references/05-adversarial-architecture-review.md",
    "references/06-final-architecture.md",
    "references/07-qc-and-smoke-testing.md",
    "references/08-implementation-roadmap.md",
    "references/09-sources-and-provenance.md",
    "references/10-scenario-routing.md",
    "references/provider-bindings.json",
    "references/scenario-profiles.json",
    "references/scenario-claude-code-opus-4.8.md",
    "references/scenario-claude-code-sonnet-5.md",
    "references/scenario-codex-gpt-5.6-sol.md",
    "scripts/resolve_scenario.py", "scripts/test_resolve_scenario.py",
)
EXPECTED_SCENARIOS = {
    "claude-code-opus-4.8", "claude-code-sonnet-5", "codex-gpt-5.6-sol"
}
FRONTMATTER_RE = re.compile(r"\A---\n(?P<body>.*?)\n---\n", re.DOTALL)
TOKEN_RE = re.compile(r"[_\s]+")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def package_root() -> Path:
    return Path(__file__).resolve().parents[1]


def normalize_token(value: str) -> str:
    return re.sub(r"-+", "-", TOKEN_RE.sub("-", value.strip().lower()))


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


def check_skill_metadata(root: Path) -> list[Finding]:
    path = root / "SKILL.md"
    if not path.is_file():
        return []
    match = FRONTMATTER_RE.match(path.read_text(encoding="utf-8"))
    if not match:
        return [Finding("ERROR", "frontmatter", "SKILL.md must begin with YAML frontmatter")]
    values: dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            return [Finding("ERROR", "frontmatter", f"unsupported line: {line!r}")]
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    findings: list[Finding] = []
    if set(values) != {"name", "description"}:
        findings.append(Finding("ERROR", "frontmatter-fields", repr(sorted(values))))
    if values.get("name") != "agent-project-orchestrator":
        findings.append(Finding("ERROR", "skill-name", "name must be agent-project-orchestrator"))
    if len(values.get("description", "")) < 80:
        findings.append(Finding("ERROR", "description-short", "description must explain scope and triggers"))
    return findings


def normalize_bindings(data: object) -> list[dict[str, object]]:
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("unsupported provider binding schema")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, list) or not capabilities:
        raise ValueError("capabilities must be a non-empty list")
    return capabilities


def check_provider_bindings(root: Path) -> tuple[list[Finding], list[dict[str, object]]]:
    try:
        capabilities = normalize_bindings(load_json(root / "references/provider-bindings.json"))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        return [Finding("ERROR", "provider-bindings", str(exc))], []
    findings: list[Finding] = []
    names: set[str] = set()
    valid_modes = {"model", "user", "user-or-model-adapter", "native-tool", "prompt-adapter", "runtime"}
    for capability in capabilities:
        if not isinstance(capability, dict):
            findings.append(Finding("ERROR", "capability-shape", repr(capability)))
            continue
        name = capability.get("name")
        providers = capability.get("providers")
        if not isinstance(name, str) or not name:
            findings.append(Finding("ERROR", "capability-name", repr(name)))
            continue
        if name in names:
            findings.append(Finding("ERROR", "duplicate-capability", name))
        names.add(name)
        if not isinstance(providers, list) or not providers:
            findings.append(Finding("ERROR", "providers", name))
            continue
        for provider in providers:
            if not isinstance(provider, dict):
                findings.append(Finding("ERROR", "provider-shape", name))
                continue
            if provider.get("invocation_mode") not in valid_modes:
                findings.append(Finding("ERROR", "invocation-mode", str(provider.get("id"))))
            harnesses = provider.get("harnesses")
            if not isinstance(harnesses, list) or not harnesses:
                findings.append(Finding("ERROR", "provider-harnesses", str(provider.get("id"))))
    return findings, capabilities


def check_scenario_profiles(root: Path) -> tuple[list[Finding], list[dict[str, object]]]:
    try:
        data = load_json(root / "references/scenario-profiles.json")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [Finding("ERROR", "scenario-profiles", str(exc))], []
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        return [Finding("ERROR", "scenario-profiles", "unsupported schema")], []
    if not isinstance(data.get("policy_floor"), dict) or not data["policy_floor"]:
        return [Finding("ERROR", "scenario-profiles", "missing policy_floor")], []
    scenarios = data.get("scenarios")
    if not isinstance(scenarios, list):
        return [Finding("ERROR", "scenario-profiles", "scenarios must be a list")], []
    findings: list[Finding] = []
    ids: set[str] = set()
    aliases: dict[tuple[str, str], str] = {}
    valid_modes = {"router_preselected", "router_preselected_with_recorded_skips", "adaptive_within_approved_graph"}
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            findings.append(Finding("ERROR", "scenario-shape", repr(scenario)))
            continue
        scenario_id = scenario.get("id")
        harness = scenario.get("harness")
        model = scenario.get("model")
        if not isinstance(scenario_id, str) or not isinstance(harness, str) or not isinstance(model, dict):
            findings.append(Finding("ERROR", "scenario-identity", repr(scenario_id)))
            continue
        if scenario_id in ids:
            findings.append(Finding("ERROR", "duplicate-scenario", scenario_id))
        ids.add(scenario_id)
        canonical = model.get("canonical")
        model_aliases = model.get("aliases", [])
        if not isinstance(canonical, str) or not isinstance(model_aliases, list):
            findings.append(Finding("ERROR", "scenario-model", scenario_id))
            continue
        for alias in [canonical, *model_aliases]:
            if not isinstance(alias, str):
                findings.append(Finding("ERROR", "scenario-model-alias", scenario_id))
                continue
            key = (normalize_token(harness), normalize_token(alias))
            owner = aliases.get(key)
            if owner is not None and owner != scenario_id:
                findings.append(Finding("ERROR", "duplicate-scenario-alias", f"{key[0]} / {key[1]}"))
            aliases[key] = scenario_id
        reference = scenario.get("scenario_reference")
        if not isinstance(reference, str) or not (root / reference).is_file():
            findings.append(Finding("ERROR", "scenario-reference", f"{scenario_id}: {reference!r}"))
        orchestration = scenario.get("orchestration")
        if not isinstance(orchestration, dict) or orchestration.get("capability_selection") not in valid_modes:
            findings.append(Finding("ERROR", "scenario-orchestration", scenario_id))
        if not isinstance(scenario.get("approval_gates"), list) or not scenario["approval_gates"]:
            findings.append(Finding("ERROR", "scenario-approval-gates", scenario_id))
    if ids != EXPECTED_SCENARIOS:
        findings.append(Finding("ERROR", "scenario-set", f"expected {sorted(EXPECTED_SCENARIOS)}, got {sorted(ids)}"))
    if not findings:
        findings.append(Finding("PASS", "scenario-profiles", f"validated {len(scenarios)} scenarios"))
    return findings, scenarios


def discover_entrypoint(candidate: str, roots: Iterable[Path]) -> Path | None:
    for root in roots:
        direct = root / candidate
        if direct.is_file():
            return direct
        matches = list(root.glob(f"**/{candidate}"))
        if matches:
            return matches[0]
    return None


def scenario_by_id(scenarios: list[dict[str, object]], scenario_id: str) -> dict[str, object] | None:
    return next((item for item in scenarios if item.get("id") == scenario_id), None)


def check_provider_discovery(capabilities: list[dict[str, object]], roots: list[Path], strict: bool, profile: str, harness: str | None) -> list[Finding]:
    if not roots:
        return [Finding("ERROR" if strict else "WARN", "provider-roots", "no --skills-root supplied; providers not discovered")]
    findings: list[Finding] = []
    for capability in capabilities:
        name = str(capability.get("name"))
        required = profile in capability.get("required_profiles", [])
        providers = capability.get("providers", [])
        compatible = [p for p in providers if isinstance(p, dict) and (harness is None or harness in p.get("harnesses", []))]
        resolved = []
        for provider in compatible:
            for candidate in provider.get("entrypoint_candidates", []):
                found = discover_entrypoint(str(candidate), roots)
                if found:
                    resolved.append(f"{provider.get('id')} -> {found}")
                    break
        if resolved:
            findings.append(Finding("PASS", "provider-resolved", f"{name}: {resolved[0]}"))
        elif required and strict:
            suffix = f" for harness {harness}" if harness else ""
            findings.append(Finding("ERROR", "required-provider-missing", f"{name}{suffix}"))
        else:
            findings.append(Finding("WARN", "provider-unresolved", name))
    return findings


def run(root: Path, skill_roots: list[Path], strict: bool, profile: str, scenario_id: str | None = None) -> list[Finding]:
    findings = check_required_files(root) + check_skill_metadata(root)
    scenario_findings, scenarios = check_scenario_profiles(root)
    findings.extend(scenario_findings)
    selected = None
    if scenario_id:
        selected = scenario_by_id(scenarios, scenario_id)
        if selected is None:
            findings.append(Finding("ERROR", "unknown-scenario", scenario_id))
        elif profile not in selected.get("supported_profiles", []):
            findings.append(Finding("ERROR", "scenario-profile", f"{scenario_id}: {profile}"))
        else:
            findings.append(Finding("PASS", "scenario-selected", scenario_id))
    binding_findings, capabilities = check_provider_bindings(root)
    findings.extend(binding_findings)
    if capabilities:
        harness = str(selected.get("harness")) if selected else None
        findings.extend(check_provider_discovery(capabilities, skill_roots, strict, profile, harness))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=package_root())
    parser.add_argument("--skills-root", action="append", default=[], type=Path)
    parser.add_argument("--profile", choices=("standard", "autonomous"), default="standard")
    parser.add_argument("--scenario")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    findings = run(args.root.resolve(), [p.resolve() for p in args.skills_root], args.strict, args.profile, args.scenario)
    for finding in findings:
        print(f"{finding.level}: {finding.code}: {finding.message}")
    errors = [item for item in findings if item.level == "ERROR"]
    if errors:
        print(f"BLOCKED: {len(errors)} error(s)", file=sys.stderr)
        return 1
    warnings = [item for item in findings if item.level == "WARN"]
    print(f"READY_WITH_DEGRADATION: {len(warnings)} warning(s)" if warnings else "READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
