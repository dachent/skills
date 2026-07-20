"""Explicit work-root paths for code-mapper-skill.

The mapper never selects a persistent cache location on its own. The caller must
provide a work root, normally the active-session bootstrap directory. Generated
reports, parser caches, and optional CodeQL data remain below that root.
"""
from __future__ import annotations

import os
from pathlib import Path

_HERE = Path(__file__).resolve()
SKILL_ROOT = _HERE.parents[1]
REPO_ROOT = _HERE.parents[2]
REQUIREMENTS_FILE = SKILL_ROOT / "scripts" / "requirements.txt"

_WORK_ROOT: Path | None = None


def configure_work_root(value: str | Path | None = None) -> Path:
    """Configure the only permitted location for generated mapper state."""
    global _WORK_ROOT
    selected = value or os.environ.get("CODE_MAPPER_WORK_ROOT")
    if not selected:
        raise ValueError(
            "code-mapper requires --work-root or CODE_MAPPER_WORK_ROOT; use an "
            "active-session .codex-bootstrap or .claude-bootstrap directory"
        )
    root = Path(selected).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    _WORK_ROOT = root
    return root


def require_work_root() -> Path:
    if _WORK_ROOT is None:
        return configure_work_root()
    return _WORK_ROOT


def io_path(path: Path) -> str:
    """Return a Windows extended-length spelling of the same contained path."""
    resolved = str(path.resolve())
    if os.name != "nt" or resolved.startswith("\\\\?\\"):
        return resolved
    if resolved.startswith("\\\\"):
        return "\\\\?\\UNC\\" + resolved[2:]
    return "\\\\?\\" + resolved


def logical_path(path: Path) -> Path:
    """Remove a Windows extended-length prefix for containment comparisons."""
    value = str(path)
    if value.startswith("\\\\?\\UNC\\"):
        value = "\\\\" + value[8:]
    elif value.startswith("\\\\?\\"):
        value = value[4:]
    return Path(value).resolve()


def is_within_work_root(path: Path) -> bool:
    return logical_path(path).is_relative_to(require_work_root().resolve())


def target_cache_dir(target_path: Path) -> Path:
    import hashlib

    root = require_work_root()
    resolved = target_path.resolve()
    digest = hashlib.sha1(str(resolved).encode("utf-8")).hexdigest()[:12]
    logical_directory = root / "reports" / f"{resolved.name}-{digest}"
    directory = Path(io_path(logical_directory))
    directory.mkdir(parents=True, exist_ok=True)
    return directory
