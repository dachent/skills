"""Shared path constants for code-mapper-skill scripts. Keeps every write location in one place."""
from pathlib import Path

_HERE = Path(__file__).resolve()
SKILL_ROOT = _HERE.parents[1]
REPO_ROOT = _HERE.parents[2]

ANALYSIS_CLONES_DIR = Path(r"C:\Dev\analysis-clones")
CACHE_ROOT = REPO_ROOT / ".dep-map-cache"
# Kept off the OneDrive-synced repo path on purpose: parso's cache filenames are a
# 64+64 char double-hash, and under the deep OneDrive path that pushed some full
# paths past Windows' 260-char MAX_PATH, causing FileNotFoundError on write even
# though the directory existed. Unrelated to where grimp/jedi themselves are
# installed -- this is jedi's own parse cache, not a package location.
JEDI_CACHE_DIR = Path(r"C:\Dev\bootstrap-state\code-mapper-skill-jedi-cache")
# grimp's own default cache_dir is the relative string ".grimp_cache" -- resolved
# against whatever the process CWD happens to be, not tied to the target being
# analyzed. Left unset, it silently writes a .grimp_cache/ folder wherever these
# scripts are invoked *from*. Pinning it to an explicit absolute path fixes that
# for good, and keeps it off OneDrive for the same reasons as the jedi cache.
GRIMP_CACHE_DIR = Path(r"C:\Dev\bootstrap-state\code-mapper-skill-grimp-cache")

REQUIREMENTS_FILE = SKILL_ROOT / "scripts" / "requirements.txt"


def target_cache_dir(target_path: Path) -> Path:
    import hashlib

    digest = hashlib.sha1(str(target_path).encode("utf-8")).hexdigest()[:12]
    d = CACHE_ROOT / f"{target_path.name}-{digest}"
    d.mkdir(parents=True, exist_ok=True)
    return d
