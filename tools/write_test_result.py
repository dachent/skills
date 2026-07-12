from __future__ import annotations

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Write a standardized per-skill CI result.")
    parser.add_argument("--skill", required=True)
    parser.add_argument(
        "--status",
        required=True,
        choices=["passed", "failed", "cancelled", "skipped"],
    )
    parser.add_argument("--authority", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--detail", action="append", default=[])
    args = parser.parse_args()
    result = {
        "schema_version": 1,
        "skill": args.skill,
        "status": args.status,
        "authority": args.authority,
        "structural_only": False,
        "runner": {
            "os": platform.system().lower(),
            "platform": sys.platform,
            "machine": platform.machine(),
            "name": os.environ.get("RUNNER_NAME"),
        },
        "git": {
            "sha": os.environ.get("GITHUB_SHA"),
            "ref": os.environ.get("GITHUB_REF"),
            "run_id": os.environ.get("GITHUB_RUN_ID"),
        },
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "details": args.detail,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
