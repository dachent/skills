from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import urllib.request
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / ".upstream" / "anthropic-skills.lock.json"
API_ENDPOINT_ROOT = "repos/anthropics/skills"


def request_json(endpoint: str) -> dict:
    gh = shutil.which("gh")
    if gh is not None:
        result = subprocess.run(
            [gh, "api", endpoint],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if result.returncode == 0:
            return json.loads(result.stdout.decode("utf-8"))
        message = result.stderr.decode("utf-8", errors="replace").strip()
        print(f"gh api request failed; falling back to unauthenticated HTTP: {message}")

    url = f"https://api.github.com/{endpoint.lstrip('/')}"
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "dachent-skills-alignment",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def get_current_upstream_sha(branch: str) -> str:
    data = request_json(f"{API_ENDPOINT_ROOT}/commits/{branch}")
    return data["sha"]


def list_tree(commit: str) -> dict[str, str]:
    data = request_json(f"{API_ENDPOINT_ROOT}/git/trees/{commit}?recursive=1")
    tree: dict[str, str] = {}
    for item in data["tree"]:
        if item.get("type") == "blob":
            tree[item["path"]] = item["sha"]
    return tree


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    digest.update(path.read_bytes())
    return digest.hexdigest()


def local_tree(root: Path) -> dict[str, str]:
    if not root.exists():
        return {}
    tree: dict[str, str] = {}
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        tree[rel] = file_hash(path)
    return tree


def compare_trees(left: dict[str, str], right: dict[str, str]) -> dict[str, list[str]]:
    left_paths = set(left)
    right_paths = set(right)
    common = left_paths & right_paths
    return {
        "added": sorted(right_paths - left_paths),
        "removed": sorted(left_paths - right_paths),
        "changed": sorted(path for path in common if left[path] != right[path]),
    }


def filtered_tree(tree: dict[str, str], prefix: str) -> dict[str, str]:
    prefix = prefix.rstrip("/")
    result: dict[str, str] = {}
    for path, sha in tree.items():
        if path == prefix:
            result[""] = sha
        elif path.startswith(prefix + "/"):
            result[path[len(prefix) + 1 :]] = sha
    return result


def build_report() -> dict:
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    upstream = lock["upstreams"]["anthropic-skills"]
    pinned_commit = upstream["commit"]
    branch = upstream["branch_at_fetch"]
    current_commit = get_current_upstream_sha(branch)

    pinned_tree = list_tree(pinned_commit)
    current_tree = list_tree(current_commit)

    skills: list[dict] = []
    for name, skill in sorted(lock["skills"].items()):
        upstream_path = skill["upstream_path"]
        local_path = skill["local_path"]
        snapshot_root = REPO_ROOT / ".upstream" / "anthropic-skills" / pinned_commit / upstream_path
        local_root = REPO_ROOT / local_path

        pinned_upstream = filtered_tree(pinned_tree, upstream_path)
        current_upstream = filtered_tree(current_tree, upstream_path)
        snapshot_files = local_tree(snapshot_root)
        local_files = local_tree(local_root)

        upstream_changes = compare_trees(pinned_upstream, current_upstream)
        local_vs_snapshot = compare_trees(snapshot_files, local_files)

        status = "ok"
        if not snapshot_root.is_dir():
            status = "missing_snapshot"
        elif not (local_root / "PROVENANCE.md").is_file():
            status = "missing_provenance"
        elif any(upstream_changes.values()) or any(local_vs_snapshot.values()):
            status = "review_required"

        skills.append(
            {
                "name": name,
                "source": skill["source"],
                "local_path": local_path,
                "upstream_path": upstream_path,
                "snapshot_present": snapshot_root.is_dir(),
                "provenance_present": (local_root / "PROVENANCE.md").is_file(),
                "upstream_changes_since_pin": upstream_changes,
                "local_vs_snapshot": local_vs_snapshot,
                "status": status,
            }
        )

    return {
        "schema_version": 1,
        "pinned_upstream_commit": pinned_commit,
        "current_upstream_commit": current_commit,
        "upstream_changed": current_commit != pinned_commit,
        "skills": skills,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", required=True, help="Path to write JSON report")
    args = parser.parse_args(argv)

    report = build_report()
    output_path = Path(args.json)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote drift report to {output_path}")
    if report["upstream_changed"]:
        print("WARNING: upstream has changed since the pinned commit.")
    for skill in report["skills"]:
        if skill["status"] != "ok":
            print(f"REVIEW: {skill['name']} status is {skill['status']}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
