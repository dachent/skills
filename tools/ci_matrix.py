from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPO_ROOT / "skills-manifest.json"
RUNNERS_BY_PLATFORM = {
    "cross-platform": ("ubuntu-latest", "windows-latest", "macos-latest"),
    "linux": ("ubuntu-latest",),
    "windows": ("windows-latest",),
    "macos": ("macos-latest",),
}
SPECIALIZED_WORKFLOWS = {
    "code-mapper-skill": ".github/workflows/code-mapper-codeql.yml",
}
FULL_VALIDATION_PATHS = {
    "skills-manifest.json",
    "tools/ci_matrix.py",
    "tools/run_skill_validation.py",
    "tools/write_test_result.py",
    "tools/repository