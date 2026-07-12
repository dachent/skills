from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "skills-manifest.json"
DEFAULT_REGISTRY = REPO_ROOT / ".provenance" / "source-registry.json"
SPECIALIZED = {"code-mapper-skill"}
CHECKS = [
    ("manifest", [sys.executable, "tools/validate_skill_manifest.py"]),
    ("generated_artifacts", [sys.executable, "tools/generate_repository_artifacts.py", "--check"]),
    ("provenance", [sys.executable, "tools/validate_provenance.py"]),
    ("actions_policy", [sys.executable, "tools/validate_actions.py"]),
]


def run_check(name: str, argv: list[str], repo_root: Path) -> dict[str, Any]:
    completed = subprocess.run(
        argv,
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "name": name,
        "status": "passed" if completed.returncode == 0 else "failed",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def stale_review_days(value: str) -> int:
    reviewed = date.fromisoformat(value)
    return (datetime.now(timezone.utc).date() - reviewed).days


def inventory_findings(
    manifest: dict[str, Any], registry: dict[str, Any], stale_after: int
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    registered = set(registry.get("skills", {}))
    for skill in manifest.get("skills", []):
        if skill.get("status") != "supported":
            continue
        name = skill.get("name", "<unknown>")
        validation = skill.get("validation", {})
        hosted = validation.get("hosted_commands", []) if isinstance(validation, dict) else []
        if not hosted and name not in SPECIALIZED:
            findings.append(
                {
                    "severity": "warning",
                    "category": "tests",
                    "skill": name,
                    "message": "no hosted command or specialized workflow",
                }
            )
        if name not in registered:
            findings.append(
                {
                    "severity": "error",
                    "category": "provenance",
                    "skill": name,
                    "message": "missing source-registry entry",
                }
            )
        reviewed = skill.get("last_reviewed")
        try:
            age = stale_review_days(reviewed)
        except (TypeError, ValueError):
            findings.append(
                {
                    "severity": "error",
                    "category": "review",
                    "skill": name,
                    "message": "invalid last_reviewed date",
                }
            )
        else:
            if age > stale_after:
                findings.append(
                    {
                        "severity": "warning",
                        "category": "review",
                        "skill": name,
                        "message": f"review is {age} days old",
                    }
                )
    return findings


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Repository health report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"Overall status: **{report['status']}**",
        "",
        "## Validator results",
        "",
        "| Check | Status |",
        "| --- | --- |",
    ]
    lines.extend(f"| `{check['name']}` | `{check['status']}` |" for check in report["checks"])
    lines.extend(["", "## Findings", ""])
    if report["findings"]:
        lines.extend(
            f"- **{item['severity']} / {item['category']}** — `{item['skill']}`: {item['message']}"
            for item in report["findings"]
        )
    else:
        lines.append("No repository-health findings.")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate repository health without duplicating validators."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--repo-root", type=Path, default=REPO_ROOT)
    parser.add_argument("--json", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, required=True)
    parser.add_argument("--stale-after-days", type=int, default=180)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    registry = json.loads(args.registry.read_text(encoding="utf-8"))
    checks = [run_check(name, command, repo_root) for name, command in CHECKS]
    findings = inventory_findings(manifest, registry, args.stale_after_days)
    has_errors = any(check["status"] == "failed" for check in checks) or any(
        item["severity"] == "error" for item in findings
    )
    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed" if has_errors else ("warning" if findings else "healthy"),
        "checks": checks,
        "findings": findings,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.markdown.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(render_markdown(report), encoding="utf-8")
    print(f"Repository health: {report['status']}")
    return 1 if has_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
