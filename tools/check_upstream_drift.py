from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / ".provenance" / "source-registry.json"


def request_json(endpoint: str) -> dict:
    gh = shutil.which("gh")
    if gh:
        result = subprocess.run([gh, "api", endpoint], capture_output=True, check=False)
        if result.returncode == 0:
            return json.loads(result.stdout.decode("utf-8"))
    request = urllib.request.Request(
        f"https://api.github.com/{endpoint.lstrip('/')}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "dachent-skills-drift"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def tree(repository: str, revision: str) -> dict[str, str]:
    payload = request_json(f"repos/{repository}/git/trees/{revision}?recursive=1")
    return {item["path"]: item["sha"] for item in payload.get("tree", []) if item.get("type") == "blob"}


def scoped(tree_map: dict[str, str], prefix: str) -> dict[str, str]:
    prefix = prefix.strip("/")
    if prefix in {"", "."}:
        return tree_map
    result: dict[str, str] = {}
    for path, sha in tree_map.items():
        if path == prefix:
            result[""] = sha
        elif path.startswith(prefix + "/"):
            result[path[len(prefix) + 1 :]] = sha
    return result


def delta(before: dict[str, str], after: dict[str, str]) -> dict[str, list[str]]:
    left, right = set(before), set(after)
    return {
        "added": sorted(right - left),
        "removed": sorted(left - right),
        "changed": sorted(path for path in left & right if before[path] != after[path]),
    }


def build_report() -> dict:
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    source_reports: dict[str, dict] = {}
    for source_id, source in sorted(registry["sources"].items()):
        if source["kind"] != "github":
            status = "manual-review-required" if source["license_review"] == "restricted-pending-review" else "not-checkable"
            source_reports[source_id] = {"kind": source["kind"], "pinned_revision": source["revision"], "status": status}
            continue
        repository = source["repository"]
        pinned = source["revision"]
        current = request_json(f"repos/{repository}/commits/{source['default_branch']}")["sha"]
        source_reports[source_id] = {
            "kind": "github",
            "repository": repository,
            "pinned_revision": pinned,
            "current_revision": current,
            "changed": current != pinned,
            "status": "review-required" if current != pinned else "aligned",
        }

    cache: dict[tuple[str, str], dict[str, str]] = {}
    skills: list[dict] = []
    for name, record in sorted(registry["skills"].items()):
        source_id = record.get("source")
        if source_id is None:
            skills.append({"name": name, "status": "repository-owned", "impacted": False})
            continue
        source = registry["sources"][source_id]
        source_report = source_reports[source_id]
        if source["kind"] != "github":
            impacted = source_report["status"] == "manual-review-required"
            skills.append({"name": name, "source": source_id, "source_path": record["source_path"], "status": source_report["status"], "impacted": impacted})
            continue
        repository = source["repository"]
        pinned = source["revision"]
        current = source_report["current_revision"]
        for revision in (pinned, current):
            cache.setdefault((repository, revision), tree(repository, revision))
        changes = delta(scoped(cache[(repository, pinned)], record["source_path"]), scoped(cache[(repository, current)], record["source_path"]))
        impacted = any(changes.values())
        skills.append({
            "name": name,
            "source": source_id,
            "source_path": record["source_path"],
            "status": "review-required" if impacted else "aligned",
            "impacted": impacted,
            "changes": changes,
        })

    impacted = [item["name"] for item in skills if item["impacted"]]
    return {"schema_version": 1, "sources": source_reports, "skills": skills, "review_required": bool(impacted), "impacted_skills": impacted}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True)
    args = parser.parse_args()
    report = build_report()
    output = Path(args.json)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote drift report to {output}")
    if report["review_required"]:
        print("REVIEW REQUIRED: " + ", ".join(report["impacted_skills"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
