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
    "linux": ("