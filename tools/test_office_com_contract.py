from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def normalize_workflow_text(text: str) -> str:
    return text.replace("\\", "/")


def require_contains(text: str, expected: str, context: