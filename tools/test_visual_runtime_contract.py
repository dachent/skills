from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_ROOT = REPO_ROOT / ".shared" / "visual-runtime"


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def require_file(relative_path: str, failures: list[str]) -> None:
    if not (REPO_ROOT / relative_path).is_file():
        failures.append(f"missing file: {relative_path}")


def require_contains(text: str, expected: str, context: str, failures: list[str]) -> None:
    if expected not in text:
        failures.append(f"{context}: missing expected text: {expected}")


def validate_contract(failures: list[str]) -> None:
    contract = read(".shared/visual-runtime/CONTRACT.md")
    for expected in [
        "# Shared Visual Runtime Contract",
        "## Design Upskill Contribution",
        "render the artifact in a real browser",
        "inspect screenshots, console output, and exported PDFs",
        "detect layout, accessibility, and asset defects",
        "preserve evidence",
        "No Office COM is required.",
        "tools/test_visual_runtime_contract.py",
    ]:
        require_contains(contract, expected, ".shared/visual-runtime/CONTRACT.md", failures)


def validate_files(failures: list[str]) -> None:
    required = [
        ".shared/visual-runtime/CONTRACT.md",
        ".shared/visual-runtime/package.json",
        ".shared/visual-runtime/package-lock.json",
        ".shared/visual-runtime/requirements.txt",
        ".shared/visual-runtime/scripts/capture_page.mjs",
        ".shared/visual-runtime/scripts/export_pdf.mjs",
        ".shared/visual-runtime/scripts/visual_lint.mjs",
        ".shared/visual-runtime/scripts/image_bounds.py",
        ".shared/visual-runtime/scripts/make_contact_sheet.py",
        ".shared/visual-runtime/references/visual-qa-loop.md",
        ".shared/visual-runtime/references/screenshot-protocol.md",
        ".shared/visual-runtime/references/accessibility-checks.md",
        ".shared/visual-runtime/references/design-tokens.md",
        ".shared/visual-runtime/tests/fixtures/sample-page.html",
        ".shared/visual-runtime/tests/fixtures/visual-runtime-brief.json",
    ]
    for relative_path in required:
        require_file(relative_path, failures)


def validate_package_metadata(failures: list[str]) -> None:
    package_path = RUNTIME_ROOT / "package.json"
    lock_path = RUNTIME_ROOT / "package-lock.json"
    if not package_path.is_file() or not lock_path.is_file():
        return

    package = json.loads(package_path.read_text(encoding="utf-8"))
    lock = json.loads(lock_path.read_text(encoding="utf-8"))

    if package.get("private") is not True:
        failures.append(".shared/visual-runtime/package.json: private must be true.")
    if package.get("type") != "module":
        failures.append(".shared/visual-runtime/package.json: type must be module.")
    if "playwright" not in package.get("devDependencies", {}):
        failures.append(".shared/visual-runtime/package.json: devDependencies.playwright is required.")
    if "check" not in package.get("scripts", {}):
        failures.append(".shared/visual-runtime/package.json: scripts.check is required.")

    packages = lock.get("packages")
    if not isinstance(packages, dict) or "node_modules/playwright" not in packages:
        failures.append(".shared/visual-runtime/package-lock.json: node_modules/playwright entry is required.")


def validate_scripts(failures: list[str]) -> None:
    script_expectations = {
        ".shared/visual-runtime/scripts/capture_page.mjs": [
            "chromium.launch",
            "page.screenshot",
            "console-events.json",
            "request-failures.json",
            "manifest.json",
        ],
        ".shared/visual-runtime/scripts/export_pdf.mjs": [
            "chromium.launch",
            "page.pdf",
            "printBackground",
        ],
        ".shared/visual-runtime/scripts/visual_lint.mjs": [
            "text_overflow",
            "low_contrast",
            "missing_image_alt",
            "visual_lint",
        ],
        ".shared/visual-runtime/scripts/image_bounds.py": [
            "read_png_size",
            "read_jpeg_size",
            "read_gif_size",
            "inspect_image",
        ],
        ".shared/visual-runtime/scripts/make_contact_sheet.py": [
            "build_html",
            "contact sheet",
            "inspect_image",
        ],
    }
    for relative_path, expected_items in script_expectations.items():
        text = read(relative_path)
        for expected in expected_items:
            require_contains(text, expected, relative_path, failures)
        if "ComObject" in text or "office_com" in text:
            failures.append(f"{relative_path}: visual runtime must not instantiate or depend on Office COM.")


def validate_readme_and_workflow(failures: list[str]) -> None:
    readme = read("README.md")
    validate_workflow = read(".github/workflows/validate.yml")
    for expected in [
        ".shared/visual-runtime",
        "render-inspect-lint-revise",
        "Node.js",
        "test_visual_runtime_contract.py",
    ]:
        require_contains(readme, expected, "README.md", failures)
    for expected in [
        "Validate shared visual runtime",
        "actions/setup-node",
        "npm ci --ignore-scripts",
        "npm run check",
        "python .\\tools\\test_visual_runtime_contract.py",
    ]:
        require_contains(validate_workflow, expected, ".github/workflows/validate.yml", failures)


def main() -> int:
    failures: list[str] = []
    validate_contract(failures)
    validate_files(failures)
    validate_package_metadata(failures)
    validate_scripts(failures)
    validate_readme_and_workflow(failures)

    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        return 1

    print("Visual runtime contract validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
