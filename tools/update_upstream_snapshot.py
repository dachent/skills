from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = REPO_ROOT / ".upstream" / "anthropic-skills.lock.json"
ARCHIVE_URL = "https://codeload.github.com/anthropics/skills/zip/{commit}"
ARCHIVE_ENDPOINT = "repos/anthropics/skills/zipball/{commit}"


def download_archive_with_gh(commit: str) -> bytes | None:
    gh = shutil.which("gh")
    if gh is None:
        return None
    result = subprocess.run(
        [gh, "api", ARCHIVE_ENDPOINT.format(commit=commit)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode == 0:
        return result.stdout
    message = result.stderr.decode("utf-8", errors="replace").strip()
    print(f"gh api archive download failed; falling back to codeload: {message}")
    return None


def download_archive(commit: str) -> bytes:
    # Prefer the installed/authenticated GitHub CLI so local and CI runs use
    # GitHub credentials instead of unauthenticated archive requests.
    archive = download_archive_with_gh(commit)
    if archive is not None:
        return archive

    req = urllib.request.Request(
        ARCHIVE_URL.format(commit=commit),
        headers={
            "User-Agent": "dachent-skills-alignment",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return response.read()


def load_lock() -> dict:
    return json.loads(LOCK_PATH.read_text(encoding="utf-8"))


def get_snapshot_targets(lock: dict) -> list[str]:
    targets: list[str] = []
    for skill in lock["skills"].values():
        if skill.get("source") == "anthropic-skills" and skill.get("snapshot") is True:
            targets.append(skill["upstream_path"].rstrip("/"))
    return sorted(set(targets))


def should_copy(path: str, targets: list[str]) -> bool:
    return any(path == target or path.startswith(f"{target}/") for target in targets)


def archive_member_path(member_name: str) -> str | None:
    parts = PurePosixPath(member_name).parts
    if len(parts) < 2:
        return None
    relative_parts = parts[1:]
    if any(part in {"", ".", ".."} for part in relative_parts):
        raise RuntimeError(f"Unsafe archive member path: {member_name}")
    return "/".join(relative_parts)


def ensure_under_root(path: Path, root: Path) -> None:
    resolved_path = path.resolve(strict=False)
    resolved_root = root.resolve(strict=False)
    if resolved_path != resolved_root and resolved_root not in resolved_path.parents:
        raise RuntimeError(f"Snapshot path escapes target root: {path}")


def write_snapshot(commit: str, targets: list[str], dry_run: bool) -> list[str]:
    root = REPO_ROOT / ".upstream" / "anthropic-skills" / commit
    copied: list[str] = []

    if not dry_run:
        for target in targets:
            target_root = root / target
            ensure_under_root(target_root, root)
            if target_root.exists():
                shutil.rmtree(target_root)

    archive = download_archive(commit)
    with zipfile.ZipFile(io.BytesIO(archive)) as zip_file:
        for member in zip_file.infolist():
            if member.is_dir():
                continue
            path = archive_member_path(member.filename)
            if path is None or not should_copy(path, targets):
                continue
            destination = root / path
            ensure_under_root(destination, root)
            copied.append(str(destination.relative_to(REPO_ROOT)).replace("\\", "/"))
            if dry_run:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(zip_file.read(member))
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    lock = load_lock()
    commit = lock["upstreams"]["anthropic-skills"]["commit"]
    targets = get_snapshot_targets(lock)
    copied = write_snapshot(commit, targets, args.dry_run)

    for path in copied:
        print(path)
    print(f"{'Would copy' if args.dry_run else 'Copied'} {len(copied)} upstream files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
