"""Locate and invoke the built XlsxWinSupervisor.exe / XlsxWinWorker.exe.

Promoted out of certification/excel_safety.py (issue #71) so control_plane's
`cli.py run` subcommand and the certification scripts (run_corpus.py,
benchmark.py) share exactly one implementation of executable-resolution and
subprocess invocation, instead of each maintaining its own copy.

This module deliberately contains **no** Excel-launch safety gate: no
opt-in-env-var check, no preflight "is Excel already running" check, no
postflight "did Excel really exit" check. Those remain
certification-specific policy, layered on top by
certification/excel_safety.py, which now imports find_built_exe/
run_supervisor from here rather than reimplementing them. Any caller of this
module -- including control_plane/cli.py's `run` subcommand -- is
responsible for applying whatever safety gate its own context requires
*before* calling run_supervisor. (cli.py's `run` subcommand does not itself
apply excel_safety's opt-in/preflight gate: unlike the certification
scripts, which are a shared, unattended test harness, `run` is an explicit,
one-shot, interactively-invoked command -- the same trust model as a human
opening Excel by hand. It still never reinterprets the supervisor's own
exit-code contract, and a caller who wants the same guardrails can layer
excel_safety.preflight_or_raise()/assert_no_excel_survives() around it
exactly as the certification scripts do.)
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

_SUPERVISOR_ROOT = Path(__file__).resolve().parent.parent / "supervisor"

# Deployment-override environment variables: if set, used verbatim instead
# of searching the dev-tree bin/** layout `dotnet build` produces. See
# xlsx-win/README.md, "Locating the built supervisor/worker executables",
# for the full deployment story. XLSXWIN_WORKER_EXE_PATH is also the
# variable run_supervisor sets on the child process's environment to tell
# XlsxWinSupervisor.exe which worker binary to launch (see
# supervisor/README.md, "Locating the worker executable") -- reusing the
# same name for both purposes is intentional: if a caller already pins this
# variable to a specific worker build, that is also the exact path
# find_built_exe resolves and passes through, with no second source of
# truth.
SUPERVISOR_PATH_ENV_VAR = "XLSXWIN_SUPERVISOR_EXE_PATH"
WORKER_PATH_ENV_VAR = "XLSXWIN_WORKER_EXE_PATH"

_EXE_PATH_ENV_VARS = {
    "XlsxWinSupervisor": SUPERVISOR_PATH_ENV_VAR,
    "XlsxWinWorker": WORKER_PATH_ENV_VAR,
}


class SupervisorLaunchError(RuntimeError):
    """Raised when invoking the built supervisor executable itself goes
    wrong at the process level -- currently, only when it does not exit
    within the caller's hard wall-clock timeout. Distinct from a job that
    runs to completion and reports failure in result.json: that is a normal
    (if unsuccessful) outcome the caller reads from the result document, not
    an error at this layer."""


def find_built_exe(project_name: str) -> Path:
    """Locate the built `<project_name>.exe`.

    Resolution order:

    1. The project's deployment-override environment variable
       (`XLSXWIN_SUPERVISOR_EXE_PATH` for `XlsxWinSupervisor`,
       `XLSXWIN_WORKER_EXE_PATH` for `XlsxWinWorker`), if set. Must point at
       an existing file -- this raises immediately rather than silently
       falling back to a dev-tree search that could resolve to a different,
       unintended build.
    2. The newest `<project_name>.exe` under
       `xlsx-win/supervisor/<project_name>/bin/**` -- the layout a plain
       `dotnet build` produces.

    Raises FileNotFoundError with a clear message (naming the offending env
    var, or pointing at `dotnet build`) if neither resolves.
    """
    env_var = _EXE_PATH_ENV_VARS.get(project_name)
    if env_var:
        override = os.environ.get(env_var)
        if override:
            override_path = Path(override)
            if override_path.is_file():
                return override_path
            raise FileNotFoundError(
                f"{env_var} is set to {override!r}, but that file does not exist. "
                "Unset it or point it at a real built executable."
            )

    candidate_root = _SUPERVISOR_ROOT / project_name
    if candidate_root.is_dir():
        matches = sorted(
            candidate_root.rglob(f"{project_name}.exe"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if matches:
            return matches[0]

    env_hint = f" and {env_var} is not set" if env_var else ""
    raise FileNotFoundError(
        f"Could not locate {project_name}.exe under {candidate_root}{env_hint}. "
        f"Build the solution first: dotnet build {_SUPERVISOR_ROOT / 'XlsxWinSupervisor.slnx'}"
    )


@dataclass(frozen=True)
class SupervisorRunResult:
    exit_code: int
    stdout: str
    stderr: str
    elapsed_seconds: float


def run_supervisor(
    job_path: Path,
    events_path: Path,
    result_path: Path,
    hard_timeout_seconds: float,
    extra_env: dict | None = None,
) -> SupervisorRunResult:
    """Launch the built XlsxWinSupervisor.exe against a job/events/result path
    triple, per xlsx-win/supervisor/README.md's file-path contract.

    Resolves both executables via find_built_exe (raising FileNotFoundError
    if either is missing) before launching anything. The caller is
    responsible for any Excel-launch safety gate its own context requires
    (opt-in env var, "Excel not already running" preflight, "Excel really
    exited" postflight) -- this function only resolves the executables, runs
    the process, and reports what happened.

    If the process somehow does not exit within hard_timeout_seconds (it
    should always exit well before this given the supervisor's own Job
    Object deadline enforcement), this is a caller-level safety net only: it
    terminates the exact supervisor.exe process this call itself started --
    never anything found by enumerating processes by name.
    """
    supervisor_exe = find_built_exe("XlsxWinSupervisor")
    worker_exe = find_built_exe("XlsxWinWorker")

    env = dict(os.environ)
    env[WORKER_PATH_ENV_VAR] = str(worker_exe)
    if extra_env:
        env.update(extra_env)

    start = time.monotonic()
    proc = subprocess.Popen(
        [str(supervisor_exe), str(job_path), str(events_path), str(result_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        stdout, stderr = proc.communicate(timeout=hard_timeout_seconds)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        elapsed = time.monotonic() - start
        raise SupervisorLaunchError(
            f"XlsxWinSupervisor did not exit within the hard timeout of {hard_timeout_seconds}s "
            f"(elapsed {elapsed:.1f}s). This indicates the supervisor's own deadline enforcement "
            "did not work. The exact process this call started was force-killed as a caller-level "
            "safety net; this is not a by-name process kill."
        )

    elapsed = time.monotonic() - start
    return SupervisorRunResult(
        exit_code=proc.returncode, stdout=stdout, stderr=stderr, elapsed_seconds=elapsed
    )
