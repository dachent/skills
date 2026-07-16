#!/usr/bin/env python3
"""Low-overhead local capability and Graphify freshness preflight.

Unlike route.py this is a real runnable entry point on purpose: it does
irreducible I/O (git rev-parse + status, GRAPH_REPORT.md read, `which` lookups)
that Claude consumes by running the command and reading the JSON verdict.
Bundling that work + the freshness state machine into one process is fewer
spawns and round-trips than doing the checks piecemeal. argparse is avoided
(one optional positional arg does not justify ~20ms of import startup);
`inspect` stays importable for test_preflight.py.

This script intentionally does not parse graph.json.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

BUILT_COMMIT = re.compile(r"Built from commit:\s*`?([0-9a-fA-F]{7,40})`?")


def _git(repo: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _report_commit(report: Path) -> str | None:
    if not report.is_file():
        return None
    try:
        text = report.read_text(encoding="utf-8", errors="replace")[:65536]
    except OSError:
        return None
    match = BUILT_COMMIT.search(text)
    return match.group(1) if match else None


def inspect(repo: Path) -> dict:
    repo = repo.resolve()
    graph_dir = repo / "graphify-out"
    graph = graph_dir / "graph.json"
    report = graph_dir / "GRAPH_REPORT.md"
    semantic_flag = graph_dir / "needs_update"
    root_marker = graph_dir / ".graphify_root"

    head = _git(repo, "rev-parse", "HEAD")
    raw_dirty = _git(repo, "status", "--porcelain")
    dirty_lines = []
    for line in (raw_dirty or "").splitlines():
        path_text = line[3:].strip().replace("\\", "/") if len(line) >= 4 else line
        if path_text == "graphify-out" or path_text.startswith("graphify-out/"):
            continue
        dirty_lines.append(line)
    dirty = "\n".join(dirty_lines)
    built_commit = _report_commit(report)

    if not graph.exists():
        state = "missing"
    elif not graph.is_file() or graph.stat().st_size == 0:
        state = "corrupt"
    elif semantic_flag.exists():
        state = "semantic_stale"
    elif head and built_commit and not head.startswith(built_commit) and not built_commit.startswith(head):
        state = "code_stale"
    elif dirty:
        state = "code_stale"
    elif head and built_commit:
        state = "fresh"
    else:
        state = "unknown"

    root_value = None
    if root_marker.is_file():
        try:
            root_value = root_marker.read_text(encoding="utf-8", errors="replace").strip() or None
        except OSError:
            pass

    return {
        "repository": str(repo),
        "git": {"head": head, "dirty": bool(dirty)},
        "graphify": {
            "executable": shutil.which("graphify"),
            "graphPath": str(graph),
            "graphExists": graph.is_file(),
            "graphBytes": graph.stat().st_size if graph.is_file() else 0,
            "builtCommit": built_commit,
            "rootMarker": root_value,
            "needsSemanticUpdate": semantic_flag.exists(),
            "state": state,
        },
        "providers": {
            "codeMapperPresent": (repo / "code-mapper-skill" / "scripts" / "blast_radius.py").is_file(),
            "codeql": shutil.which("codeql"),
        },
        "policy": {
            "parsedGraphJson": False,
            "safeForExactMapperFastPath": True,
        },
    }


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("-h", "--help"):
        print("usage: preflight.py [REPO]   # REPO defaults to '.'")
        return
    repo = args[0] if args else "."
    print(json.dumps(inspect(Path(repo)), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
