#!/usr/bin/env python3
"""Alternate baseline and candidate commands and report wall-time overhead."""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import time
from dataclasses import asdict, dataclass


@dataclass
class Summary:
    samplesSeconds: list[float]
    medianSeconds: float
    p95Seconds: float


def run(command: str, timeout: int) -> float:
    start = time.perf_counter()
    result = subprocess.run(
        command,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
    )
    elapsed = time.perf_counter() - start
    if result.returncode != 0:
        raise RuntimeError(f"command failed: {command}\n{result.stderr}")
    return elapsed


def summarize(samples: list[float]) -> Summary:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(0.95 * len(ordered) + 0.999) - 1))
    return Summary(samples, statistics.median(samples), ordered[index])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--warmups", type=int, default=2)
    parser.add_argument("--runs", type=int, default=15)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-median-delta-ms", type=float, default=75.0)
    parser.add_argument("--max-median-delta-percent", type=float, default=5.0)
    parser.add_argument("--max-p95-delta-ms", type=float, default=200.0)
    args = parser.parse_args()

    samples = {"baseline": [], "candidate": []}
    for round_index in range(args.warmups + args.runs):
        order = [("baseline", args.baseline), ("candidate", args.candidate)]
        if round_index % 2:
            order.reverse()
        for name, command in order:
            elapsed = run(command, args.timeout)
            if round_index >= args.warmups:
                samples[name].append(elapsed)

    base = summarize(samples["baseline"])
    candidate = summarize(samples["candidate"])
    median_delta = candidate.medianSeconds - base.medianSeconds
    p95_delta = candidate.p95Seconds - base.p95Seconds
    percent = median_delta / base.medianSeconds * 100 if base.medianSeconds else None
    result = {
        "baseline": asdict(base),
        "candidate": asdict(candidate),
        "medianDeltaSeconds": median_delta,
        "medianDeltaPercent": percent,
        "p95DeltaSeconds": p95_delta,
        "gates": {
            "maxMedianDeltaMs": args.max_median_delta_ms,
            "maxMedianDeltaPercent": args.max_median_delta_percent,
            "maxP95DeltaMs": args.max_p95_delta_ms,
        },
    }
    print(json.dumps(result, indent=2))
    failed = median_delta * 1000 > args.max_median_delta_ms
    failed |= percent is not None and percent > args.max_median_delta_percent
    failed |= p95_delta * 1000 > args.max_p95_delta_ms
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
