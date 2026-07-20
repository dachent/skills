"""Resolve local, read-only analysis targets without network or Git mutation."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

_URL_PREFIX_RE = re.compile(r"^(https?://|ssh://|git@)", re.IGNORECASE)


def looks_like_git_url(value: str) -> bool:
    return bool(_URL_PREFIX_RE.match(value)) or value.endswith(".git")


def resolve(path_or_url: str) -> Path:
    if looks_like_git_url(path_or_url):
        raise ValueError(
            "Git URL targets are disabled: use the approved centralized-Git workflow "
            "to create an explicit local worktree, then pass that local path. "
            "code-mapper never clones, fetches, or pulls repositories."
        )
    path = Path(path_or_url).expanduser().resolve()
    if not path.is_dir():
        raise FileNotFoundError(f"not a local directory: {path_or_url!r}")
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("path_or_url")
    args = parser.parse_args()
    print(resolve(args.path_or_url))


if __name__ == "__main__":
    main()
