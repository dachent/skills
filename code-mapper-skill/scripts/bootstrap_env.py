"""Read-only dependency preflight for code-mapper-skill."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import sys

REQUIRED = {"grimp": "3.15", "jedi": "0.20.0"}


def dependency_status() -> dict[str, dict[str, str | bool | None]]:
    status: dict[str, dict[str, str | bool | None]] = {}
    for name, required in REQUIRED.items():
        available = importlib.util.find_spec(name) is not None
        version = None
        if available:
            try:
                version = importlib.metadata.version(name)
            except importlib.metadata.PackageNotFoundError:
                pass
        status[name] = {
            "available": available,
            "version": version,
            "required": required,
            "matches": available and version == required,
        }
    return status


def assert_dependencies() -> None:
    status = dependency_status()
    problems = [
        f"{name}=={record['required']} (found {record['version'] or 'missing'})"
        for name, record in status.items()
        if not record["matches"]
    ]
    if problems:
        raise RuntimeError(
            "Mapper dependency preflight failed: "
            + ", ".join(problems)
            + ". Provision scripts/requirements.txt in an explicitly approved "
            "C:\\Tools\\code-mapper runtime or session-local virtual environment; "
            "the mapper never runs pip automatically."
        )


def main() -> None:
    assert_dependencies()
    print(f"pinned dependencies available in {sys.executable}")


if __name__ == "__main__":
    main()
