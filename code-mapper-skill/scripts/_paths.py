"""Shared path constants for code-mapper-skill scripts.

All machine-level paths are configurable and default to the operating system's normal
per-user cache location. Target repositories remain read-only.
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()
SKILL_ROOT = _HERE.parents[1]
REPO_ROOT = _HERE.parents[2]


def _user_cache_root() -> Path:
    explicit = os.environ.get("CODE_MAPPER_CACHE_HOME")
    if explicit:
        return Path(explicit).expanduser().resolve()
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / "dachent-skills" / "code-mapper"
        return Path.home() / "AppData" / "Local" / "dachent-skills" / "code-mapper"
    if sys_platform() == "darwin":
        return Path.home() / "Library" / "Caches" / "dachent-skills" / "code-mapper"
    base = os.environ.get("XDG_CACHE_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".cache") / "dachent-skills" / "code-mapper"


def sys_platform() -> str:
    import sys

    return sys.platform


def _configured_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser().resolve() if value else default


USER_CACHE_ROOT = _user_cache_root()
ANALYSIS_CLONES_DIR = _configured_path("CODE_MAPPER_CLONE_HOME", USER_CACHE_ROOT / "clones")
CACHE_ROOT = _configured_path("CODE_MAPPER_REPORT_HOME", REPO_ROOT / ".dep-map-cache")
JEDI_CACHE_DIR = _configured_path("CODE_MAPPER_JEDI_CACHE_HOME", USER_CACHE_ROOT / "jedi")
GRIMP_CACHE_DIR = _configured_path("CODE_MAPPER_GRIMP_CACHE_HOME", USER_CACHE_ROOT / "grimp")
REQUIREMENTS_FILE = SKILL_ROOT / "scripts" / "requirements.txt"


def target_cache_dir(target_path: Path) -> Path:
    import hashlib

    digest = hashlib.sha1(str(target_path).encode("utf-8")).hexdigest()[:12]
    directory = CACHE_ROOT / f"{target_path.name}-{digest}"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
