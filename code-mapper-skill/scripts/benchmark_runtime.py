"""Compare complete blast_radius.py wall time between two code-mapper checkouts.

Example:
  python scripts/benchmark_runtime.py BASE/code-mapper-skill CANDIDATE/code-mapper-skill REPO io.py --subdir pkg --package pkg

The runner alternates baseline/candidate order to reduce drift. Use --cold to clear
each checkout's code-mapper caches before every measured run. The optional gates
make the command exit non-zero when a candidate exceeds the accepted slowdown.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path


def clear_caches(work_root: Path) -> None:
    if work_root.exists():
        shutil.rmtree(work_root)


def command(skill_root: Path, target: Path, file_rel: str, args) -> list[str]:
    cmd = [sys.executable, str(skill_root / "scripts" / "blast_radius.py"), str(target), file_rel]
    if args.subdir:
        cmd += ["--subdir", args.subdir]
    if args.package:
        cmd += ["--package", args.package]
    if args.function:
        cmd += ["--function", args.function]
    return cmd


def run_once(skill_root: Path, target: Path, file_rel: str, args) -> float:
    work_root = args.work_root / skill_root.name
    if args.cold:
        clear_caches(work_root)
    env = os.environ.copy()
    env["CODE_MAPPER_WORK_ROOT"] = str(work_root)
    started = time.perf_counter()
    result = subprocess.run(
        command(skill_root, target, file_rel, args),
        cwd=skill_root,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=args.timeout,
        env=env,
    )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        raise RuntimeError(f"benchmark command failed for {skill_root}: {result.stderr}")
    return elapsed


def summarize(samples: list[float]) -> dict:
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, max(0, int(0.95 * (len(ordered) - 1) + 0.999)))
    return {
        "samplesSeconds": samples,
        "medianSeconds": statistics.median(samples),
        "p95Seconds": ordered[p95_index],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("baseline_skill_root", type=Path)
    ap.add_argument("candidate_skill_root", type=Path)
    ap.add_argument("target", type=Path)
    ap.add_argument("file")
    ap.add_argument("--subdir", default=None)
    ap.add_argument("--package", default=None)
    ap.add_argument("--function", default=None)
    ap.add_argument("--runs", type=int, default=7)
    ap.add_argument("--warmups", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--work-root", type=Path, required=True, help="explicit session directory for benchmark caches")
    ap.add_argument("--cold", action="store_true")
    ap.add_argument("--max-median-delta-percent", type=float, default=None)
    ap.add_argument("--max-median-delta-seconds", type=float, default=None)
    args = ap.parse_args()

    baseline_root = args.baseline_skill_root.resolve()
    candidate_root = args.candidate_skill_root.resolve()
    target = args.target.resolve()
    samples = {"baseline": [], "candidate": []}
    total_rounds = args.warmups + args.runs
    for round_index in range(total_rounds):
        order = [
            ("baseline", baseline_root),
            ("candidate", candidate_root),
        ]
        if round_index % 2:
            order.reverse()
        for name, root in order:
            elapsed = run_once(root, target, args.file, args)
            if round_index >= args.warmups:
                samples[name].append(elapsed)

    baseline = summarize(samples["baseline"])
    candidate = summarize(samples["candidate"])
    base = baseline["medianSeconds"]
    cand = candidate["medianSeconds"]
    delta = cand - base
    delta_percent = (delta / base * 100.0) if base else None
    result = {
        "mode": "cold" if args.cold else "warm",
        "baseline": baseline,
        "candidate": candidate,
        "medianDeltaSeconds": delta,
        "medianDeltaPercent": delta_percent,
    }
    print(json.dumps(result, indent=2))

    failed = False
    if args.max_median_delta_percent is not None and delta_percent is not None:
        failed |= delta_percent > args.max_median_delta_percent
    if args.max_median_delta_seconds is not None:
        failed |= delta > args.max_median_delta_seconds
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
