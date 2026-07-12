from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".provenance" / "source-registry.json"
MANIFEST = ROOT / "skills-manifest.json"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
EXTERNAL = {"local-source-import", "light-adaptation", "medium-adaptation", "heavy-adaptation", "derived-work"}
VALID_REVIEWS = {"reviewed", "reviewed-with-boundaries", "restricted-pending-review"}
VALID_DISTRIBUTIONS = {"MIT", "source-license-boundary", "restricted", "repository-policy"}


def load(path: Path, failures: list[str]) -> dict:
    if not path.is_file():
        failures.append(f"missing file: {path.relative_to(ROOT)}")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"invalid JSON in {path.relative_to(ROOT)}: {exc}")
        return {}
    if not isinstance(value, dict):
        failures.append(f"{path.relative_to(ROOT)} must contain an object")
        return {}
    return value


def text(obj: dict, key: str, context: str, failures: list[str]) -> str | None:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        failures.append(f"{context}: missing non-empty '{key}'")
        return None
    return value


def main() -> int:
    failures: list[str] = []
    registry = load(REGISTRY, failures)
    manifest = load(MANIFEST, failures)
    if not registry or not manifest:
        for item in failures:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1

    if registry.get("schema_version") != 1:
        failures.append("source registry schema_version must be 1")

    policy = registry.get("repository_license")
    if not isinstance(policy, dict):
        failures.append("repository_license must be an object")
    else:
        text(policy, "status", "repository_license", failures)
        document = text(policy, "policy_document", "repository_license", failures)
        text(policy, "default_for_repo_owned_originals", "repository_license", failures)
        if document and not (ROOT / document).is_file():
            failures.append(f"repository license policy does not exist: {document}")

    sources = registry.get("sources")
    if not isinstance(sources, dict) or not sources:
        failures.append("sources must be a non-empty object")
        sources = {}
    for source_id, source in sorted(sources.items()):
        context = f"sources.{source_id}"
        if not isinstance(source, dict):
            failures.append(f"{context}: must be an object")
            continue
        kind = text(source, "kind", context, failures)
        revision = text(source, "revision", context, failures)
        text(source, "retrieved_on", context, failures)
        text(source, "license", context, failures)
        review = text(source, "license_review", context, failures)
        if revision and not SHA_RE.fullmatch(revision):
            failures.append(f"{context}.revision must be a 40-character lowercase SHA")
        if review and review not in VALID_REVIEWS:
            failures.append(f"{context}.license_review is unsupported: {review}")
        if kind == "github":
            text(source, "repository", context, failures)
            text(source, "default_branch", context, failures)
        if review == "reviewed":
            evidence = text(source, "license_evidence", context, failures)
            if evidence and not (ROOT / evidence).is_file():
                failures.append(f"{context}: missing license evidence: {evidence}")

    records = registry.get("skills")
    if not isinstance(records, dict) or not records:
        failures.append("skills must be a non-empty object")
        records = {}
    manifest_skills = {item.get("name"): item for item in manifest.get("skills", []) if isinstance(item, dict)}
    supported = {name for name, item in manifest_skills.items() if item.get("status") == "supported"}
    missing = sorted(supported - set(records))
    extra = sorted(set(records) - set(manifest_skills))
    if missing:
        failures.append("supported skills missing provenance records: " + ", ".join(missing))
    if extra:
        failures.append("provenance records not present in manifest: " + ", ".join(extra))

    for name, record in sorted(records.items()):
        context = f"skills.{name}"
        if not isinstance(record, dict):
            failures.append(f"{context}: must be an object")
            continue
        classification = text(record, "classification", context, failures)
        text(record, "port_depth", context, failures)
        text(record, "intentional_divergence", context, failures)
        text(record, "owner", context, failures)
        text(record, "last_alignment_review", context, failures)
        distribution = text(record, "distribution", context, failures)
        if distribution and distribution not in VALID_DISTRIBUTIONS:
            failures.append(f"{context}.distribution is unsupported: {distribution}")
        source_id = record.get("source")
        source_path = record.get("source_path")
        if classification in EXTERNAL:
            if not isinstance(source_id, str) or source_id not in sources:
                failures.append(f"{context}: external derivative must reference a registered source")
            if not isinstance(source_path, str) or not source_path.strip():
                failures.append(f"{context}: external derivative must record source_path")
            if source_id in sources and sources[source_id].get("license_review") == "restricted-pending-review" and distribution != "restricted":
                failures.append(f"{context}: unresolved source licensing requires restricted distribution")
        elif source_id is not None or source_path is not None:
            failures.append(f"{context}: repo-owned original must not reference an external source")

    if failures:
        for item in failures:
            print(f"ERROR: {item}", file=sys.stderr)
        return 1
    print(f"Provenance validation passed for {len(records)} skills and {len(sources)} sources.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
