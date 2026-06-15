#!/usr/bin/env python3
"""Regression tests for the Codex deep-planning artifact validator."""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    validator_path = (
        REPO_ROOT
        / "deep-planning-codex"
        / "scripts"
        / "validate_deep_planning_artifacts.py"
    )
    if validator_path.exists():
        spec = importlib.util.spec_from_file_location(
            "deep_planning_validator", validator_path
        )
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load {validator_path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    raise FileNotFoundError("Could not find deep-planning validator")


def write_file(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.strip() + "\n", encoding="utf-8")


def write_base_artifacts(root: Path, *, state_text: str, review_text: str) -> None:
    planning = root / ".deep-planning"
    planning.mkdir(parents=True, exist_ok=True)

    for name in (
        "harness-preflight.md",
        "success-criteria.md",
        "failure-criteria.md",
        "out-of-scope.md",
        "repo-map.md",
        "evidence-catalog.md",
        "assumption-ledger.md",
        "verification-plan.md",
        "implementation-plan.md",
    ):
        write_file(planning, name, f"# {name}\nplaceholder")

    write_file(planning, "project-mode.md", "# Project Mode\nsoftware-no-git")
    write_file(planning, "state.md", state_text)
    write_file(planning, "adversarial-review.md", review_text)


def valid_state() -> str:
    return """
    # Deep Planning State

    Project mode: software-no-git
    Current phase: final planning
    Status: READY_FOR_PROCEED

    ## Updated Artifacts
    - .deep-planning/state.md

    ## Decisions
    - Continue.

    ## Open Assumptions
    - None.

    ## Next Action
    Wait for PROCEED.
    """


def test_rejects_incomplete_state_fields() -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_base_artifacts(
            root,
            state_text="""
            # Deep Planning State
            Project mode: software-no-git
            Status: READY_FOR_PROCEED
            """,
            review_text="""
            # Adversarial Plan Review

            ## Verdict
            PASS
            """,
        )

        issues = validator.validate(root)

    assert any("Current phase" in issue for issue in issues), issues
    assert any("Next Action" in issue for issue in issues), issues


def test_rejects_failed_adversarial_review_for_ready_state() -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_base_artifacts(
            root,
            state_text=valid_state(),
            review_text="""
            # Adversarial Plan Review

            ## Verdict
            FAIL

            ## Findings
            - **Severity**: BLOCKING
            - **Issue**: Critical path unverified.
            - **Evidence**: Fixture.
            - **Required fix**: Verify before execution.
            """,
        )

        issues = validator.validate(root)

    assert any("adversarial-review.md verdict must be PASS" in issue for issue in issues), issues
    assert any("BLOCKING" in issue for issue in issues), issues


def test_accepts_complete_ready_packet() -> None:
    validator = load_validator()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        write_base_artifacts(
            root,
            state_text=valid_state(),
            review_text="""
            # Adversarial Plan Review

            ## Verdict
            PASS

            ## Findings
            - **Severity**: NOTE
            - **Issue**: No blocking issue.
            - **Evidence**: Fixture.
            - **Required fix**: None.
            """,
        )

        issues = validator.validate(root)

    assert issues == []


def run() -> int:
    tests = [
        test_rejects_incomplete_state_fields,
        test_rejects_failed_adversarial_review_for_ready_state,
        test_accepts_complete_ready_packet,
    ]
    failures: list[str] = []
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures.append(f"{test.__name__}: {exc}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        return 1

    print(f"PASS: {len(tests)} validator regression tests")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
