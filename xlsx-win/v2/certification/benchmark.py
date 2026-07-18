#!/usr/bin/env python3
"""Benchmark: supervisor (Path A, #36) vs. the legacy `refresh_excel.ps1`, on
an equivalent open+refresh+recalc+save job, for issue #39 (single-machine
subset).

Per the issue's own instruction: this does **not** assume or assert a
specific improvement percentage. RFC 0001's "at least 30% lower automation
overhead" target was framed around eliminating *multiple* Excel launches for
one logical operation; the legacy script already consolidates into one
Excel lifecycle (open -> RefreshAll -> CalculateFullRebuild -> Save -> Close
-> Quit, read `xlsx-win/scripts/refresh_excel.ps1` yourself), so a speed win
over it for one equivalent job is not guaranteed. This script reports
whatever wall-clock numbers it actually measures, including if the new path
is not meaningfully faster -- the real value of the supervisor over the
legacy script is bounded/attributable failure and no orphan processes under
fault conditions (see the two new fault-injection integration tests this
issue adds), not necessarily raw speed for a clean run.

Deliberate deviation from a literal reading of "with at least one
refreshable connection": see certification/README.md's "Benchmark scope
deviation" section for the full reasoning. In short: this repo's own
supervisor/README.md already documents a reproduced, environment-specific
finding that any real WorkbookConnection.Refresh() on this machine can leave
EXCEL.EXE not exiting on its own for many minutes; building a benchmark
fixture with a genuinely live connection would need bespoke Excel-COM-driving
code outside the supervisor's own Job-Object-protected path, which would in
turn need its own timeout/kill safety net -- and this issue's safety rules
explicitly forbid writing any new process-kill logic. Rather than accept an
unbounded-wait risk on a real desktop just to re-demonstrate an
already-fully-documented finding, this benchmark uses a Table-with-static-data
workbook (no live connection -- built entirely by openpyxl, no Excel
involved in fixture creation at all), so `refresh` runs over zero
connections on both sides. This is a legitimate structural comparison (both
legs execute the same step shape) but not a live-connection-refresh timing
comparison; this script's own report says so explicitly, not just this
docstring.

Usage:
    XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1 python xlsx-win/v2/certification/benchmark.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
_REPO_ROOT = _V2_ROOT.parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))
_CERT_ROOT = Path(__file__).resolve().parent
if str(_CERT_ROOT) not in sys.path:
    sys.path.insert(0, str(_CERT_ROOT))

import excel_safety  # noqa: E402
from corpus import _build_table_workbook  # noqa: E402

_LEGACY_SCRIPT = _REPO_ROOT / "xlsx-win" / "scripts" / "refresh_excel.ps1"

_SUPERVISOR_TIMEOUTS = {
    "start_excel_seconds": 30,
    "open_workbook_seconds": 30,
    "refresh_total_seconds": 60,
    "calculation_seconds": 30,
    "save_seconds": 30,
    "close_seconds": 60,
}
_SUPERVISOR_HARD_TIMEOUT_SECONDS = 300
_LEGACY_HARD_TIMEOUT_SECONDS = 300


_FRACTIONAL_SECONDS_RE = re.compile(r"\.(\d+)")


def _parse_dotnet_timestamp(raw: str) -> datetime:
    """.NET's `DateTime.ToString`-derived JSON timestamps (as emitted by the
    C# worker's WorkerEvent) can carry more than 6 fractional-second digits
    (its default round-trip format uses up to 7, i.e. ticks). Python's
    datetime.fromisoformat (this repo targets 3.10, where fromisoformat is
    strict about 3 or 6 digits) rejects that, so truncate to microseconds
    before parsing rather than silently dropping every timestamp."""
    match = _FRACTIONAL_SECONDS_RE.search(raw)
    if match and len(match.group(1)) > 6:
        raw = raw[: match.start(1)] + match.group(1)[:6] + raw[match.end(1) :]
    return datetime.fromisoformat(raw)


def _events_span_seconds(events_path: Path) -> float | None:
    """Best-effort: first-to-last event timestamp span in events.jsonl, as a
    proxy for "Excel automation work time" separate from the subprocess's
    own total wall-clock time (which also includes process startup/teardown
    on the supervisor side)."""
    if not events_path.exists():
        return None

    timestamps = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
            timestamps.append(_parse_dotnet_timestamp(entry["timestamp"]))
        except (json.JSONDecodeError, KeyError, ValueError):
            continue

    if len(timestamps) < 2:
        return None
    return (max(timestamps) - min(timestamps)).total_seconds()


def _run_supervisor_leg(run_dir: Path) -> dict:
    input_path = run_dir / "supervisor_input.xlsx"
    output_path = run_dir / "supervisor_output.xlsx"
    job_path = run_dir / "supervisor_job.json"
    events_path = run_dir / "supervisor_events.jsonl"
    result_path = run_dir / "supervisor_result.json"

    _build_table_workbook(input_path)

    manifest = {
        "schema_version": "2.0",
        "idempotency_key": "benchmark-supervisor",
        "steps": [
            {"type": "open", "workbook_path": str(input_path)},
            {"type": "refresh", "connections": "all"},
            {"type": "recalc", "mode": "full_rebuild"},
            {"type": "save_as", "output_path": str(output_path), "overwrite": True},
        ],
        "timeouts": _SUPERVISOR_TIMEOUTS,
    }
    job_path.write_text(json.dumps(manifest), encoding="utf-8")

    excel_safety.preflight_or_raise()
    wall_start = time.perf_counter()
    try:
        run_result = excel_safety.run_supervisor(
            job_path, events_path, result_path, _SUPERVISOR_HARD_TIMEOUT_SECONDS
        )
    finally:
        excel_safety.assert_no_excel_survives()
    wall_seconds = time.perf_counter() - wall_start

    result_doc = None
    if result_path.exists() and result_path.stat().st_size > 0:
        result_doc = json.loads(result_path.read_text(encoding="utf-8"))

    return {
        "leg": "supervisor",
        "wall_clock_seconds": wall_seconds,
        "events_span_seconds": _events_span_seconds(events_path),
        "exit_code": run_result.exit_code,
        "ok": result_doc.get("ok") if result_doc else None,
        "final_state": result_doc.get("final_state") if result_doc else None,
    }


def _run_legacy_leg(run_dir: Path) -> dict:
    input_path = run_dir / "legacy_input.xlsx"
    json_path = run_dir / "legacy_result.json"
    log_path = run_dir / "legacy.log"

    _build_table_workbook(input_path)

    excel_safety.preflight_or_raise()
    wall_start = time.perf_counter()
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-File",
                str(_LEGACY_SCRIPT),
                "-WorkbookPath",
                str(input_path),
                "-JsonPath",
                str(json_path),
                "-LogPath",
                str(log_path),
                "-TimeoutSeconds",
                "120",
            ],
            capture_output=True,
            text=True,
            timeout=_LEGACY_HARD_TIMEOUT_SECONDS,
        )
    finally:
        excel_safety.assert_no_excel_survives()
    wall_seconds = time.perf_counter() - wall_start

    status_doc = None
    if json_path.exists():
        # refresh_excel.ps1 writes with `-Encoding UTF8`, which (PowerShell's
        # legacy behavior) includes a UTF-8 BOM; utf-8-sig strips it.
        status_doc = json.loads(json_path.read_text(encoding="utf-8-sig"))

    return {
        "leg": "legacy_refresh_excel_ps1",
        "wall_clock_seconds": wall_seconds,
        "process_exit_code": proc.returncode,
        "reported_status": status_doc.get("status") if status_doc else None,
        "reported_duration_seconds": status_doc.get("duration_seconds") if status_doc else None,
        "reported_exit_code": status_doc.get("exit_code") if status_doc else None,
    }


def main() -> int:
    run_dir = Path(tempfile.mkdtemp(prefix="xlsx-win-cert-benchmark-"))
    print(f"Benchmark artifacts: {run_dir}")
    print(
        "\nNOTE: neither leg's workbook has a live/refreshable connection -- see "
        "certification/README.md, 'Benchmark scope deviation', for why. Both legs run "
        "an equivalent open + refresh(0 connections) + recalc(full_rebuild) + save job."
    )

    try:
        supervisor_result = _run_supervisor_leg(run_dir)
    except excel_safety.ExcelSafetyError as exc:
        print(f"\nSupervisor leg did not run: {exc}")
        return 1

    print(f"\n=== Supervisor leg ===\n{json.dumps(supervisor_result, indent=2)}")

    try:
        legacy_result = _run_legacy_leg(run_dir)
    except excel_safety.ExcelSafetyError as exc:
        print(f"\nLegacy-script leg did not run: {exc}")
        return 1

    print(f"\n=== Legacy refresh_excel.ps1 leg ===\n{json.dumps(legacy_result, indent=2)}")

    print("\n=== Comparison ===")
    sup_seconds = supervisor_result["wall_clock_seconds"]
    legacy_seconds = legacy_result["wall_clock_seconds"]
    print(f"Supervisor total wall-clock:        {sup_seconds:.2f}s")
    print(f"Legacy refresh_excel.ps1 wall-clock: {legacy_seconds:.2f}s")

    supervisor_succeeded = supervisor_result.get("ok") is True
    legacy_succeeded = legacy_result.get("reported_status") == "success" and (
        legacy_result.get("reported_exit_code") == 0
    )
    if not supervisor_succeeded or not legacy_succeeded:
        print(
            "\nAt least one leg did NOT actually succeed -- the wall-clock numbers above are "
            "NOT a valid timing comparison (a failed/short-circuited run's timing is not a "
            "meaningful data point):"
        )
        if not supervisor_succeeded:
            print(
                f"  Supervisor leg did NOT succeed (ok={supervisor_result.get('ok')!r}, "
                f"final_state={supervisor_result.get('final_state')!r}, "
                f"exit_code={supervisor_result.get('exit_code')!r})."
            )
        if not legacy_succeeded:
            print(
                f"  Legacy leg did NOT succeed (reported_status="
                f"{legacy_result.get('reported_status')!r}, reported_exit_code="
                f"{legacy_result.get('reported_exit_code')!r}, process_exit_code="
                f"{legacy_result.get('process_exit_code')!r})."
            )
        return 1

    if sup_seconds < legacy_seconds:
        print(
            f"Supervisor was faster by {legacy_seconds - sup_seconds:.2f}s on this run, for this "
            "no-live-connection job shape. This is one measurement, not a statistically robust "
            "benchmark, and is not evidence of the RFC 0001 30% target (framed around eliminating "
            "multiple Excel launches for one logical operation, not a single equivalent job)."
        )
    elif sup_seconds > legacy_seconds:
        print(
            f"Supervisor was slower by {sup_seconds - legacy_seconds:.2f}s on this run. Reported "
            "honestly, as instructed -- the supervisor's real value proposition for this issue is "
            "bounded/attributable failure and no orphan processes under fault conditions (see the "
            "two new fault-injection integration tests), not necessarily raw speed for a clean run."
        )
    else:
        print("Supervisor and legacy wall-clock times were equal on this run (to two decimals).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
