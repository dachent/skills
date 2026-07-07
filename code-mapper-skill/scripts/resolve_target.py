"""Resolve a target argument (local path, or GitHub/GitLab/self-hosted git URL) to a local path.

Local paths pass through untouched (read-only, no cloning). URLs are cloned via the
centralized git tooling (C:\\Dev\\bin\\New-CentralGitClone.ps1) into C:\\Dev\\analysis-clones\\
-- never raw `git clone`, per this workstation's Git Safety Protocol. Re-running against an
already-cloned URL does a fetch+pull instead of re-cloning (the clone script refuses non-empty
target directories).
"""
import argparse
import hashlib
import re
import subprocess
from pathlib import Path

from _paths import ANALYSIS_CLONES_DIR

_URL_PREFIX_RE = re.compile(r"^(https?://|git@)", re.IGNORECASE)


def looks_like_git_url(s: str) -> bool:
    return bool(_URL_PREFIX_RE.match(s)) or s.endswith(".git")


def repo_name_from_url(url: str) -> str:
    stem = url.rstrip("/").rsplit("/", 1)[-1]
    if stem.endswith(".git"):
        stem = stem[:-4]
    return stem or "repo"


def clone_target_dir(url: str) -> Path:
    digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:8]
    return ANALYSIS_CLONES_DIR / f"{repo_name_from_url(url)}-{digest}"


def existing_clone_matches(path: Path, url: str) -> bool:
    if not (path / ".git").exists():
        return False
    result = subprocess.run(
        ["git", "-C", str(path), "remote", "get-url", "origin"],
        capture_output=True, text=True,
    )
    return result.returncode == 0 and result.stdout.strip() == url


def resolve(path_or_url: str) -> Path:
    if not looks_like_git_url(path_or_url):
        p = Path(path_or_url).resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"not a local directory and not a git URL: {path_or_url!r}")
        return p

    url = path_or_url
    target = clone_target_dir(url)

    if target.exists():
        if not existing_clone_matches(target, url):
            raise FileExistsError(
                f"{target} already exists and isn't a clone of {url} -- refusing to overwrite"
            )
        subprocess.run(["git", "-C", str(target), "fetch"], check=True)
        subprocess.run(["git", "-C", str(target), "pull"], check=True)
        return target

    ANALYSIS_CLONES_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "powershell", "-NoProfile", "-NonInteractive", "-File",
            r"C:\Dev\bin\New-CentralGitClone.ps1",
            "-RepositoryUrl", url,
            "-WorktreePath", str(target),
        ],
        check=True,
    )
    return target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path_or_url")
    args = ap.parse_args()
    print(resolve(args.path_or_url))


if __name__ == "__main__":
    main()
