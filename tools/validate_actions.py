from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPO_ROOT / ".github" / "workflows"
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
USES_RE = re.compile(r"^\s*-?\s*uses:\s*([^\s#]+)")
RUNS_ON_RE = re.compile(r"^\s*runs-on:\s*([^#]+?)\s*$")
APPROVED_RUNNERS = {"ubuntu-latest", "windows-latest", "macos-latest"}
APPROVED_SELF_HOSTED_LABELS = {"self-hosted", "windows", "office"}


def validate_workflows(root: Path = WORKFLOW_ROOT) -> list[str]:
    errors: list[str] = []
    paths = sorted(root.glob("*.yml")) + sorted(root.glob("*.yaml"))
    for path in paths:
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(REPO_ROOT).as_posix()
        if "permissions:" not in text:
            errors.append(f"{rel}: missing explicit permissions")
        if "timeout-minutes:" not in text:
            errors.append(f"{rel}: missing timeout-minutes")
        if "concurrency:" not in text:
            errors.append(f"{rel}: missing concurrency policy")
        lines = text.splitlines()
        for index, line in enumerate(lines):
            line_number = index + 1
            uses = USES_RE.match(line)
            if uses:
                target = uses.group(1)
                if target.startswith("./"):
                    continue
                if "@" not in target:
                    errors.append(f"{rel}:{line_number}: external action has no ref: {target}")
                    continue
                ref = target.rsplit("@", 1)[1]
                if not SHA_RE.fullmatch(ref):
                    errors.append(
                        f"{rel}:{line_number}: external action is not pinned to a 40-character SHA: {target}"
                    )
            runner = RUNS_ON_RE.match(line)
            if runner:
                value = runner.group(1).strip().strip("'\"")
                if value.startswith("${{") or value in APPROVED_RUNNERS:
                    continue
                if value.startswith("[") or value == "":
                    continue
                errors.append(f"{rel}:{line_number}: unapproved runner expression: {value}")
            if re.match(r"^\s*runs-on:\s*$", line):
                indentation = len(line) - len(line.lstrip())
                labels: set[str] = set()
                for following in lines[index + 1 :]:
                    following_indent = len(following) - len(following.lstrip())
                    if following.strip() and following_indent <= indentation:
                        break
                    stripped = following.strip()
                    if stripped.startswith("-"):
                        labels.add(stripped[1:].strip().strip("'\""))
                if labels != APPROVED_SELF_HOSTED_LABELS:
                    errors.append(
                        f"{rel}:{line_number}: self-hosted runner labels must be "
                        f"{sorted(APPROVED_SELF_HOSTED_LABELS)}, found {sorted(labels)}"
                    )
        if "actions/checkout@" in text and "persist-credentials: false" not in text:
            errors.append(f"{rel}: checkout must set persist-credentials: false")
    return errors


def main() -> int:
    errors = validate_workflows()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("GitHub Actions policy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
