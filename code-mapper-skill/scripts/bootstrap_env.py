"""Ensures grimp/jedi are importable in the ambient Python environment (the one running
these scripts). Installs from requirements.txt into that same environment only if missing --
no --target, no venv. On this machine they're already pip-installed system-wide."""
import subprocess
import sys

from _paths import REQUIREMENTS_FILE


def already_installed() -> bool:
    try:
        import grimp  # noqa: F401
        import jedi  # noqa: F401
    except ImportError:
        return False
    return True


def main() -> None:
    if already_installed():
        print(f"grimp/jedi already importable in {sys.executable}, skipping")
        return

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(REQUIREMENTS_FILE)],
        check=True,
    )
    print(f"installed into {sys.executable}")


if __name__ == "__main__":
    main()
