"""Shared Excel-launch safety gate for the certification scripts
(run_corpus.py, benchmark.py).

This is the Python-side equivalent of the C# integration tests'
`ExcelIntegrationGate` (see
`xlsx-win/v2/supervisor/XlsxWinSupervisor.IntegrationTests/`), reused here so
both certification scripts apply the exact same rules rather than each
reimplementing them slightly differently:

1. Refuse to run (raise) unless XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1 is set
   in the environment -- reusing issue #36's exact opt-in convention rather
   than inventing a second one, per this issue's own safety rules.
2. Refuse to run (raise) if an EXCEL.EXE process is already running.
3. After a run, poll for and confirm zero surviving EXCEL.EXE processes.

Excel-process detection here is read-only (a count, via PowerShell
Get-Process), used only to decide whether to proceed (1) or to verify
cleanup happened (3) -- never to select a kill target. No code in this
module enumerates Excel processes in order to terminate them; the only
termination logic anywhere in this issue's scope is the supervisor's
existing Job Object mechanism (`JobObjectHandle.cs`), invoked here only by
running the supervisor executable as a subprocess.

Executable-resolution and subprocess-invocation (find_built_exe,
SupervisorRunResult, the core of run_supervisor) used to be defined here,
but were promoted to `control_plane/supervisor_runner.py` (issue #71) so
`control_plane/cli.py`'s `run` subcommand and this module share one
implementation instead of maintaining two. This module now only adds the
Excel-specific safety gate (opt-in + preflight + postflight) around that
shared implementation; `run_supervisor` below still raises this module's
own `ExcelSafetyError` on a supervisor-launch failure, exactly as it did
before the refactor, so existing callers (run_corpus.py, benchmark.py) that
catch `ExcelSafetyError` around this call keep working unchanged.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

_V2_ROOT = Path(__file__).resolve().parent.parent
if str(_V2_ROOT) not in sys.path:
    sys.path.insert(0, str(_V2_ROOT))

from control_plane.supervisor_runner import (  # noqa: E402
    SupervisorLaunchError,
    SupervisorRunResult,
    find_built_exe,
)
from control_plane.supervisor_runner import run_supervisor as _run_supervisor_impl  # noqa: E402

RUN_ENV_VAR = "XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS"


class ExcelSafetyError(RuntimeError):
    """Raised when a safety precondition (opt-in flag, Excel-not-already-running,
    no-survivor-after-run) is not met. Never caught silently by callers --
    this must stop the run, not degrade into a warning."""


def excel_process_count() -> int:
    """Count of currently running EXCEL.EXE processes, via a read-only
    PowerShell Get-Process query. Never used to select a kill target."""
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            "(Get-Process -Name EXCEL -ErrorAction SilentlyContinue | Measure-Object).Count",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    output = (result.stdout or "").strip()
    try:
        return int(output)
    except ValueError:
        # Treat an unparseable/empty result as "unknown, assume none" only if
        # PowerShell itself reported success; a nonzero PowerShell exit is a
        # harness problem, not evidence either way, so fail loudly instead of
        # silently proceeding.
        if result.returncode != 0:
            raise ExcelSafetyError(
                f"Could not determine whether Excel is running (PowerShell exit "
                f"{result.returncode}): {result.stderr.strip()}"
            )
        return 0


def require_opt_in() -> None:
    """Raise ExcelSafetyError unless XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1 is set."""
    import os

    if os.environ.get(RUN_ENV_VAR) != "1":
        raise ExcelSafetyError(
            f"Refusing to launch Excel: set {RUN_ENV_VAR}=1 in the environment to opt in "
            "(the same convention xlsx-win/v2/supervisor's C# integration tests use). "
            "See certification/README.md."
        )


def preflight_or_raise() -> None:
    """Raise ExcelSafetyError if an EXCEL.EXE process is already running.
    Call this fresh immediately before every run -- never rely on a check
    performed earlier in the process."""
    require_opt_in()

    count = excel_process_count()
    if count > 0:
        raise ExcelSafetyError(
            f"Refusing to run: {count} EXCEL.EXE process(es) already running on this machine. "
            "Close all Excel windows and retry -- this script will not proceed alongside an "
            "instance you may be using interactively."
        )


def assert_no_excel_survives(max_wait_seconds: float = 180.0, poll_seconds: float = 0.5) -> None:
    """Poll (bounded) for Excel process teardown, then raise ExcelSafetyError
    if any EXCEL.EXE process still remains. The generous wait window mirrors
    the C# ExcelIntegrationGate.AssertNoExcelProcessSurvives -- real
    verification on this machine found Application.Quit() can return long
    before EXCEL.EXE itself actually exits after a connection refresh (see
    supervisor/README.md, "Known limitation: connection-refresh shutdown
    latency")."""
    deadline = time.monotonic() + max_wait_seconds
    while time.monotonic() < deadline:
        if excel_process_count() == 0:
            return
        time.sleep(poll_seconds)

    final_count = excel_process_count()
    if final_count != 0:
        raise ExcelSafetyError(
            f"{final_count} EXCEL.EXE process(es) still running after waiting "
            f"{max_wait_seconds}s for teardown. This is a real orphan, not a false alarm."
        )


def run_supervisor(
    job_path: Path,
    events_path: Path,
    result_path: Path,
    hard_timeout_seconds: float,
    extra_env: dict | None = None,
) -> SupervisorRunResult:
    """Launch the built XlsxWinSupervisor.exe against a job/events/result path
    triple, per xlsx-win/v2/supervisor/README.md's file-path contract.

    Caller must have already called preflight_or_raise(). This function does
    not check Excel's running state itself -- it only runs the process and
    reports what happened, mirroring the C# SupervisorRunner.

    Delegates to control_plane.supervisor_runner.run_supervisor for
    executable resolution and the actual subprocess invocation, translating
    its SupervisorLaunchError into this module's own ExcelSafetyError so
    existing callers (run_corpus.py, benchmark.py) that catch
    ExcelSafetyError around this call keep working unchanged.
    """
    try:
        return _run_supervisor_impl(job_path, events_path, result_path, hard_timeout_seconds, extra_env)
    except SupervisorLaunchError as exc:
        raise ExcelSafetyError(str(exc)) from exc
