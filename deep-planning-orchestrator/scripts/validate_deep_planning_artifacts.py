#!/usr/bin/env python3
"""Validate a target project's .deep-planning artifact set."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


VALID_STATUSES = {
    "READY_FOR_PROCEED",
    "BLOCKED_NEEDS_USER_DECISION",
    "BLOCKED_BY_MISSING_EVIDENCE",
    "FAILED_VALIDATION",
}

VALID_MODES = {
    "software-git",
    "software-no-git",
    "business-artifact",
    "mixed-business-coding",
}

BASE_REQUIRED = [
    "state.md",
    "harness-preflight.md",
    "project-mode.md",
    "success-criteria.md",
    "failure-criteria.md",
    "out-of-scope.md",
    "repo-map.md",
    "evidence-catalog.md",
    "assumption-ledger.md",
    "verification-plan.md",
    "adversarial-review.md",
]

BUSINESS_REQUIRED = [
    "stakeholder-map.md",
    "decision-log.md",
]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path} is not UTF-8 text") from exc


def value_after_prefix(text: str, prefix: str) -> str | None:
    for line in text.splitlines():
        if line.strip().lower().startswith(prefix.lower()):
            return line.split(":", 1)[1].strip()
    return None


def validate(root: Path) -> list[str]:
    issues: list[str] = []
    planning = root / ".deep-planning"

    if not planning.exists():
        return [f"Missing planning folder: {planning}"]
    if not planning.is_dir():
        return [f"Not a directory: {planning}"]

    state_path = planning / "state.md"
    mode_path = planning / "project-mode.md"

    mode = None
    if mode_path.exists():
        mode_text = read_text(mode_path)
        for candidate in VALID_MODES:
            if candidate in mode_text:
                mode = candidate
                break

    required = list(BASE_REQUIRED)
    if mode in {"business-artifact", "mixed-business-coding"}:
        required.extend(BUSINESS_REQUIRED)

    for rel in required:
        path = planning / rel
        if not path.exists():
            issues.append(f"Missing required artifact: .deep-planning/{rel}")
        elif path.is_file() and not read_text(path).strip():
            issues.append(f"Empty required artifact: .deep-planning/{rel}")

    if state_path.exists():
        state_text = read_text(state_path)
        status = value_after_prefix(state_text, "Status")
        if status not in VALID_STATUSES:
            issues.append(
                "state.md must contain Status: "
                + " | ".join(sorted(VALID_STATUSES))
            )
        state_mode = value_after_prefix(state_text, "Project mode")
        if state_mode and state_mode not in VALID_MODES:
            issues.append(
                "state.md project mode must be one of: "
                + ", ".join(sorted(VALID_MODES))
            )

    if mode_path.exists() and mode is None:
        issues.append(
            "project-mode.md must mention one valid mode: "
            + ", ".join(sorted(VALID_MODES))
        )

    review_path = planning / "adversarial-review.md"
    if review_path.exists():
        review_text = read_text(review_path)
        if "## Verdict" not in review_text:
            issues.append("adversarial-review.md must include ## Verdict")
        if not any(verdict in review_text for verdict in ("PASS", "FAIL", "PARTIAL")):
            issues.append("adversarial-review.md must include PASS, FAIL, or PARTIAL")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate .deep-planning artifacts for a target project."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Target project root containing .deep-planning",
    )
    args = parser.parse_args()

    issues = validate(Path(args.target).resolve())
    if issues:
        for issue in issues:
            print(f"ERROR: {issue}", file=sys.stderr)
        return 1

    print("Deep planning artifacts are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
