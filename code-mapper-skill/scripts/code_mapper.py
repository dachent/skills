from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from codeql_runner import CodeQLError, enrich
from mapper_core import scan_repository

HERE = Path(__file__).resolve().parent
QUERY = HERE.parent / "codeql" / "local_flows.ql"


def main() -> int:
    parser = argparse.ArgumentParser(description="Map a local Python repository")
    parser.add_argument("target", help="local repository directory")
    parser.add_argument("--deep", action="store_true", help="run explicit CodeQL local flow analysis")
    parser.add_argument("--rebuild", action="store_true", help="rebuild the CodeQL database")
    parser.add_argument("--codeql", default=None, help="CodeQL executable or installation directory")
    parser.add_argument("--output", default=None, help="write JSON to this path instead of stdout")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    try:
        graph = scan_repository(target)
        if args.deep:
            graph = enrich(target, graph, QUERY, codeql_override=args.codeql, rebuild=args.rebuild)
    except (ValueError, CodeQLError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    payload = json.dumps(graph, indent=2, sort_keys=True)
    if args.output:
        output = Path(args.output).resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(payload, encoding="utf-8")
        print(output)
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
