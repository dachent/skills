"""Resolve a local directory or Git URL to a local read-only analysis target.

Local directories pass through unchanged. Git URLs are cloned into a configurable
per-user cache directory with ordinary Git commands. Set CODE_MAPPER_CLONE_HOME to
change the clone location or CODE_MAPPER_GIT_CLONE_COMMAND to use an approved clone
wrapper; the URL and destination are appended to that command.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

from _paths import ANALYSIS_CLONES_DIR

_URL_PREFIX_RE = re.compile(r"^(https?://|ssh://|git@)", re.IGNORECASE)


def looks_like_git_url(value: str) -> bool:
    return bool(_URL_PREFIX_RE.match(value)) or value.endswith(".git")


def repo_name_from_url(url: str) -> str:
    normalized = url.rstrip("/")
    stem = normalized.rsplit("/", 1)[-1]
    if ":" in stem and normalized.startswith("git@"):
        stem = stem.rsplit(":", 1)[-1]
    if stem.endswith(".git"):
        stem = stem[:-4]
    return stem or "repo"


def clone_target_dir(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return ANALYSIS_CLONES_DIR / f"{repo_name_from_url(url)}-{digest}"


def _run(command: list[str]) -> None:
    subprocess.run(command, check=True)


def _require_git() -> str:
    git = shutil.which("git")
    if not git:
        raise RuntimeError("git is required for Git URL targets but was not found on PATH")
    return git


def existing_clone_matches(path: Path, url: str) -> bool:
    if not (path / ".git").exists():
        return False
    git = _require_git()
    result = subprocess.run(
        [git, "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == url


def _clone(url: str, target: Path) -> None:
    custom = os.environ.get("CODE_MAPPER_GIT_CLONE_COMMAND")
    if custom:
        command = shlex.split(custom, posix=os.name != "nt") + [url, str(target)]
    else:
        command = [_require_git(), "clone", "--depth", "1", url, str(target)]
    _run(command)


def _refresh(path: Path) -> None:
    git = _require_git()
    _run([git, "-C", str(path), "fetch", "--prune", "origin"])
    pull = subprocess.run(
        [git, "-C", str(path), "pull", "--ff-only"],
        capture_output=True,
        text=True,
        check=False,
    )
    if pull.returncode != 0:
        raise RuntimeError(
            "existing analysis clone could not be fast-forwarded; remove it or update it manually: "
            f"{path}\n{pull.stderr.strip()}"
        )


def resolve(path_or_url: str) -> Path:
    if not looks_like_git_url(path_or_url):
        path = Path(path_or_url).expanduser().resolve()
        if not path.is_dir():
            raise FileNotFoundError(f"not a local directory and not a Git URL: {path_or_url!r}")
        return path

    url = path_or_url
    target = clone_target_dir(url)
    if target.exists():
        if not existing_clone_matches(target, url):
            raise FileExistsError(
                f"{target} already exists and is not a clone of {url}; refusing to overwrite"
            )
        _refresh(target)
        return target

    ANALYSIS_CLONES_DIR.mkdir(parents=True, exist_ok=True)
    _clone(url, target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path_or_url")
    args = parser.parse_args()
    print(resolve(args.path_or_url))


if __name__ == "__main__":
    main()
