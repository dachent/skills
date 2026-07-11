"""Explicit-only CodeQL local-flow runner. Never used by the default scan path."""
import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from _paths import SKILL_ROOT


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("database", help="existing local Python CodeQL database")
    ap.add_argument("--output", default=None, help="CSV result path")
    args = ap.parse_args()

    codeql = shutil.which("codeql")
    if not codeql:
        print("CodeQL CLI is not installed or not on PATH; default code-mapper analysis is unaffected.", file=sys.stderr)
        return 2
    database = Path(args.database).resolve()
    if not database.is_dir():
        print(f"CodeQL database does not exist: {database}", file=sys.stderr)
        return 2
    output = Path(args.output).resolve() if args.output else database.parent / "code-mapper-local-flow.csv"
    bqrs = output.with_suffix(".bqrs")
    query = SKILL_ROOT / "codeql" / "local_artifact_flow.ql"
    subprocess.run([codeql, "query", "run", "--database", str(database), "--output", str(bqrs), str(query)], check=True)
    subprocess.run([codeql, "bqrs", "decode", "--format=csv", "--output", str(output), str(bqrs)], check=True)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
