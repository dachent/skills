#!/usr/bin/env python3
"""Resolve one supported harness/model scenario and its provider-compatible policy."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILES = ROOT / "references" / "scenario-profiles.json"
DEFAULT_BINDINGS = ROOT / "references" / "provider-bindings.json"


class ScenarioResolutionError(ValueError):
    """Raised when a scenario or provider route cannot be resolved safely."""


def normalize_token(value: str) -> str:
    normalized = re.sub(r"[_\s]+", "-", value.strip().lower())
    return re.sub(r"-+", "-", normalized)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ScenarioResolutionError(f"{path} must contain an object")
    return data


def load_profiles(path: Path = DEFAULT_PROFILES) -> dict[str, Any]:
    data = load_json(path)
    if data.get("schema_version") != 1:
        raise ScenarioResolutionError("unsupported scenario profile schema_version")
    if not isinstance(data.get("policy_floor"), dict) or not data["policy_floor"]:
        raise ScenarioResolutionError("scenario profiles require a policy_floor")
    if not isinstance(data.get("scenarios"), list) or not data["scenarios"]:
        raise ScenarioResolutionError("scenario profiles require scenarios")
    return data


def scenario_index(data: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for scenario in data["scenarios"]:
        if not isinstance(scenario, dict):
            raise ScenarioResolutionError("each scenario must be an object")
        harness = normalize_token(str(scenario.get("harness", "")))
        model = scenario.get("model")
        if not harness or not isinstance(model, dict):
            raise ScenarioResolutionError("scenario requires harness and model")
        canonical = model.get("canonical")
        aliases = model.get("aliases", [])
        if not isinstance(canonical, str) or not canonical:
            raise ScenarioResolutionError("scenario model requires canonical name")
        if not isinstance(aliases, list) or not all(isinstance(item, str) for item in aliases):
            raise ScenarioResolutionError("scenario aliases must be strings")
        for alias in [canonical, *aliases]:
            key = (harness, normalize_token(alias))
            if key in index and index[key].get("id") != scenario.get("id"):
                raise ScenarioResolutionError(f"duplicate scenario alias: {key}")
            index[key] = scenario
    return index


def resolve_scenario(
    harness: str,
    model: str,
    profile: str = "standard",
    profiles_path: Path = DEFAULT_PROFILES,
) -> tuple[dict[str, Any], dict[str, Any]]:
    data = load_profiles(profiles_path)
    scenario = scenario_index(data).get((normalize_token(harness), normalize_token(model)))
    if scenario is None:
        supported = ", ".join(sorted(str(item["id"]) for item in data["scenarios"]))
        raise ScenarioResolutionError(
            f"unsupported harness/model pair: {harness!r} / {model!r}; supported: {supported}"
        )
    profiles = scenario.get("supported_profiles", [])
    if profile not in profiles:
        raise ScenarioResolutionError(f"scenario {scenario['id']} does not support {profile!r}")
    return data, scenario


def providers_for_capability(
    bindings: dict[str, Any], capability_name: str, harness: str
) -> list[dict[str, Any]]:
    capabilities = bindings.get("capabilities", [])
    if not isinstance(capabilities, list):
        raise ScenarioResolutionError("provider capabilities must be a list")
    for capability in capabilities:
        if not isinstance(capability, dict) or capability.get("name") != capability_name:
            continue
        providers = capability.get("providers", [])
        if not isinstance(providers, list):
            raise ScenarioResolutionError(f"{capability_name}: providers must be a list")
        return [
            provider
            for provider in providers
            if isinstance(provider, dict) and harness in provider.get("harnesses", [])
        ]
    return []


def validate_capabilities(
    capabilities: Iterable[str], harness: str, bindings_path: Path = DEFAULT_BINDINGS
) -> dict[str, list[str]]:
    requested = list(dict.fromkeys(item for item in capabilities if item))
    if not requested:
        return {}
    bindings = load_json(bindings_path)
    resolved: dict[str, list[str]] = {}
    missing: list[str] = []
    for capability in requested:
        providers = providers_for_capability(bindings, capability, harness)
        if not providers:
            missing.append(capability)
        else:
            resolved[capability] = [str(item.get("id")) for item in providers]
    if missing:
        raise ScenarioResolutionError(
            f"no {harness} provider for required capabilities: {', '.join(sorted(missing))}"
        )
    return resolved


def build_resolution(
    harness: str,
    model: str,
    profile: str = "standard",
    capabilities: Iterable[str] = (),
    profiles_path: Path = DEFAULT_PROFILES,
    bindings_path: Path = DEFAULT_BINDINGS,
) -> dict[str, Any]:
    data, scenario = resolve_scenario(harness, model, profile, profiles_path)
    selected = list(dict.fromkeys(item for item in capabilities if item))
    resolved_providers = validate_capabilities(selected, str(scenario["harness"]), bindings_path)
    return {
        "schema_version": 1,
        "scenario_id": scenario["id"],
        "harness": scenario["harness"],
        "model": scenario["model"]["canonical"],
        "profile": profile,
        "scenario_reference": scenario["scenario_reference"],
        "policy_floor": data["policy_floor"],
        "orchestration": scenario["orchestration"],
        "approval_gates": scenario["approval_gates"],
        "review": scenario["review"],
        "selected_capabilities": selected,
        "provider_candidates": resolved_providers,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harness", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--profile", choices=("standard", "autonomous"), default="standard")
    parser.add_argument("--capability", action="append", default=[])
    parser.add_argument("--profiles", type=Path, default=DEFAULT_PROFILES)
    parser.add_argument("--bindings", type=Path, default=DEFAULT_BINDINGS)
    args = parser.parse_args()
    try:
        result = build_resolution(
            args.harness,
            args.model,
            args.profile,
            args.capability,
            args.profiles,
            args.bindings,
        )
    except (OSError, json.JSONDecodeError, ScenarioResolutionError) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
