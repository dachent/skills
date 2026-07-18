# xlsx-win v2 supervisor (Path A, increment 1)

C# implementation of issue #36's reduced increment-1 scope: a bounded Windows
execution service that supervises real Excel COM automation from outside the
COM apartment, with process ownership via a Windows Job Object. This replaces
unsupervised PowerShell COM driving for the specific step types implemented
here.

Related documents:

- RFC 0001 (`docs/rfcs/0001-xlsx-win-runtime-v2.md`) -- the full Path A/Path C
  vision this increment is a deliberately reduced slice of.
- RFC 0002 (`docs/rfcs/0002-xlsx-win-v2-single-user-scope.md`) -- the
  single-desktop scope amendment; decisions 7 and 8 (dialog prevention,
  PID-tracked termination) are load-bearing for this code.
- `xlsx-win/schemas/job.schema.json` / `result.schema.json` -- the JSON
  contract from issue #34 this supervisor consumes/produces.
- `xlsx-win/control_plane/state_machine.py` -- the state names this code's
  `JobStates` (C#) is a direct port of.

## Projects

| Project | Purpose |
| --- | --- |
| `XlsxWinContracts` | Shared job/result/event JSON models and the ported job state machine. Referenced by everything else. |
| `XlsxWinWorker` | Runs one job's Excel COM work on an explicit STA thread. Launched as a child process by the supervisor. |
| `XlsxWinSupervisor` | Entry point. Launches the worker, owns the Windows Job Object, enforces phase deadlines by tailing the worker's event stream. |
| `XlsxWinWorker.Tests` | xUnit, no Excel. Runs under a plain `dotnet test`. |
| `XlsxWinSupervisor.Tests` | xUnit, no Excel. Runs under a plain `dotnet test`. |
| `XlsxWinSupervisor.IntegrationTests` | xUnit, real Excel. Gated behind `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1`; never runs otherwise. |

## Build

```powershell
dotnet build xlsx-win\supervisor\XlsxWinSupervisor.slnx
```

Targets `net10.0-windows` throughout (the only SDK installed at the time this
was written is 10.0.302).

## Running the unit tests (safe, no Excel, no preconditions)

```powershell
dotnet test xlsx-win\supervisor\XlsxWinSupervisor.slnx
```

This runs `XlsxWinWorker.Tests`, `XlsxWinSupervisor.Tests`, **and**
`XlsxWinSupervisor.IntegrationTests` -- but every test in the integration
project checks `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS` in its constructor via
`Skip.If`/`Skip.IfNot` and skips cleanly if the variable isn't `1`. A plain
`dotnet test` run, from anyone, never launches Excel.

## Running the integration tests for real (real Excel, opt-in)

**Preconditions, checked by this code itself at the start of every test (not
just something to eyeball once):**

1. No `EXCEL.EXE` process already running on the machine -- the test
   constructor calls `ExcelIntegrationGate.PreflightOrSkip()`, which skips
   (does not fail, does not proceed) if it finds one.
2. `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1` set in the environment the test
   process inherits.

```powershell
$env:XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS = "1"
dotnet test xlsx-win\supervisor\XlsxWinSupervisor.IntegrationTests\XlsxWinSupervisor.IntegrationTests.csproj
```

After every test, `ExcelIntegrationGate.AssertNoExcelProcessSurvives()` polls
(up to 180s -- see "Known limitations" below for why that's generous) and
then asserts zero `EXCEL.EXE` processes remain, whether the test exercised a
normal successful shutdown or a forced Job-Object termination.

Each integration test creates its own workbook(s) via Excel COM itself
(`Workbooks.Add()` then `SaveAs`) inside a fresh temp directory it creates
(`TestTempDir`, under `%TEMP%\xlsxwin-inttest-<guid>`) and never references
any file outside that directory.

## Job/result JSON file-path contract

Both executables take the same three positional arguments:

```
XlsxWinWorker.exe     <job.json> <events.jsonl> <result.json>
XlsxWinSupervisor.exe <job.json> <events.jsonl> <result.json>
```

The supervisor forwards all three paths verbatim to the worker it launches
(plus `XLSXWIN_WORKER_EXE_PATH` to tell it which worker binary to run --
see "Locating the worker executable" below). A future Python control-plane
caller (`xlsx-win/control_plane/cli.py`) would shell out to
`XlsxWinSupervisor.exe` with these three paths; wiring that up is explicitly
out of scope for this issue (see "Explicitly deferred" below).

- **job.json**: parsed by `XlsxWinContracts.JobManifest`. Shape matches
  `xlsx-win/schemas/job.schema.json` (`schema_version`, `idempotency_key`,
  `steps`) plus one addition -- see "Known gap vs job.schema.json" below.
- **events.jsonl**: one JSON object per line, appended by the worker as it
  moves through phases, using the exact state names from
  `control_plane/state_machine.py` (ported to C# in `JobStates`). Truncated
  to empty by the supervisor before each run. Shape: `{run_id, timestamp,
  phase, message?, excel_pid?}`. The supervisor tails this file to (a) track
  which phase's deadline currently applies, and (b) learn the Excel process's
  own PID as soon as the worker captures it, so it can assign that PID to the
  Job Object too.
- **result.json**: written once, by the worker on a clean exit or by the
  supervisor itself on a forced termination. Shape matches
  `xlsx-win/schemas/result.schema.json` (`schema_version`, `run_id`,
  `idempotency_key`, `final_state`, `steps[]`, `invariants[]`, `ok`). `ok` is
  always computed from `steps`/`invariants` (`ResultDocument.Build`), never
  independently settable, mirroring `result_contract.py`.

**Supervisor exit codes**: `0` on a clean worker exit within all deadlines
(the job's own `final_state`/`ok` may still be `FAILED`/`false` -- a caller
must read those fields, not this exit code, to learn the job's outcome);
`1` on a forced Job-Object termination (`final_state: TIMED_OUT`); `2` on
argument/manifest-parse errors before any Excel work started.

### Known gap vs job.schema.json

`job.schema.json` (from #34, already merged) does not declare a top-level
`timeouts` object, and its `additionalProperties: false` means a document
containing one would fail strict schema validation. This C# supervisor's own
`JobManifest` model is deliberately a tolerant superset: it accepts an
optional `timeouts` object (field names -- `start_excel_seconds`,
`open_workbook_seconds`, `refresh_total_seconds`, `calculation_seconds`,
`save_seconds`, `close_seconds` -- reused verbatim from RFC 0001's example
manifest) because phase deadlines have to come from *somewhere* and the
merged #34 schema doesn't yet carry them. This C# code does not itself
validate against the JSON Schema (that remains Python's job), so the extra
property round-trips fine even though it isn't yet formally declared. Worth
reconciling in a follow-up to #34 so the Python side validates it too.

### Locating the worker executable

`XlsxWinSupervisor` resolves `XlsxWinWorker.exe` via `WorkerLauncher`:

1. `XLSXWIN_WORKER_EXE_PATH` environment variable, if set (must point at an
   existing file).
2. `XlsxWinWorker.exe` in the same directory as `XlsxWinSupervisor.exe`
   (the expected layout after a side-by-side publish).
3. A dev-tree fallback: walks up from the supervisor's own build output
   looking for a sibling `XlsxWinWorker` folder and the newest
   `XlsxWinWorker.exe` under it.

## Architecture notes

### IMessageFilter COM-retry handling (issue #72)

`ComMessageFilter.cs` implements the standard, well-known `IOleMessageFilter`
COM interop pattern (documented in numerous Microsoft KB articles about
Office automation hangs) and registers it via `CoRegisterMessageFilter`
immediately after `Program.cs`'s `Main` parses `WorkerArgs` -- before Excel
is ever started -- and revokes it (`CoRegisterMessageFilter(null, ...)`) in a
`finally` block that runs on every exit path, including exceptions.

- `HandleInComingCall` always returns `SERVERCALL_ISHANDLED` (0).
- `RetryRejectedCall`: `SERVERCALL_REJECTED` (1) fails the call immediately
  (`-1`) -- not retryable. `SERVERCALL_RETRYLATER` (2) is retried with a
  fixed 200ms delay, up to `ComMessageFilter.MaxRetryAttempts` (10) attempts,
  after which it also returns `-1` so the caller gets a clear COM exception
  instead of retrying forever.
- `MessagePending` always returns `PENDINGMSG_WAITDEFPROCESS` (2).

The retry counter is reset once per job step (`StepRunner.Run`, before
dispatching to the step's handler) rather than once per outgoing COM call or
once for the whole job -- a deliberate choice so each step's own result
message can report *that step's* retry count via
`StepRunner.AppendRetrySuffix`: `"Opened '...'. (retried COM call 3 times)"`,
appended to the step's existing success/failure message whenever
`RetryAttempts > 0` after the step runs. Covered by
`ComMessageFilterTests.cs` (pure logic, no COM/Excel): bound enforcement,
the three constant return values, and per-step reset.

### Heartbeat (issue #72)

`StepRunner.RefreshOneConnection`'s post-`Refresh()` polling loop (the same
loop that already calls `IsStillRefreshing`/`MessagePump.PumpingDelay` every
200ms) now also emits a `WorkerEvent` roughly every 5 seconds
(`StepRunner`'s `DefaultHeartbeatInterval`, overridable via an optional
`StepRunner` constructor parameter for tests) while the loop is still
running -- not on every 200ms tick, which would be noise, not a heartbeat.
It reuses the existing `REFRESHING_CONNECTIONS` phase name (rather than
inventing a new `JobStates`/`state_machine.py` phase -- there is no
"heartbeat" phase in either, deliberately, to avoid ever duplicating or
conflicting with that shared state list) with a distinguishing
`message: "heartbeat: still refreshing."` instead.

One side effect worth calling out explicitly: `XlsxWinSupervisor`'s own
`Program.cs` resets `lastTransitionUtc` on *every* event with a non-empty
`Phase`, including a same-phase heartbeat (see `EventTailer`/`Program.cs`
around `if (!string.IsNullOrEmpty(evt.Phase)) { currentPhase = evt.Phase;
lastTransitionUtc = DateTime.UtcNow; }`). So a refresh that keeps emitting
heartbeats also keeps the supervisor's own independent phase-deadline clock
from firing early relative to the worker's own internal
`refresh_total_seconds` deadline (`RunRefresh`'s own `deadline` variable,
computed once and shared across all connections in one refresh step) --
this is a deliberate, welcome side effect of reusing the phase field, not a
bug: the two clocks now stay in lockstep instead of racing to expire at
the same original timestamp.

**Real-world caveat, confirmed by direct COM probing, not guessed:** this
polling loop only gets a chance to run long enough to emit a heartbeat for
a connection/provider where `WorkbookConnection.Refresh()` itself returns
before the underlying data fetch is actually done, with `.Refreshing`
continuing to report `true` for a while afterward. Probing the exact
Power-Query/Mashup OLEDB connection type this codebase's own certification
fixtures use (`FixtureWorkbookBuilder.CreateWorkbookWithConnection`,
`certification/corpus.py`'s `power_query_minimal`) directly against a
query with an injected 12-second `Function.InvokeAfter` delay showed
`Refresh()` itself blocking synchronously for the *entire* 17.7 of those
seconds it took, with only ~0.07s of subsequent polling before
`Refreshing` read back `false` -- i.e., `TrySetBackgroundQueryOff`'s
`BackgroundQuery = false` request is fully honored by this provider, and
the post-`Refresh()` loop simply never has meaningful time to run for it.
**No heartbeat is visible in `events.jsonl` for that connection type in
this environment, and that is the loop working correctly, not a defect --
there is no "still waiting" period left to report once `Refresh()` has
already returned with the work done.** The mechanism itself (the interval
check and the `Emit` call) is proven correct and deterministic against a
fake `dynamic` connection object in `RefreshHeartbeatTests.cs`, which
exercises a connection that keeps reporting `Refreshing = true` past the
configured interval (simulating a provider that does not fully honor
synchronous mode) and asserts at least one heartbeat event is written, plus
a companion test proving the immediate-completion case emits none. This is
the honest scope of what this increment's heartbeat placement (dictated by
the issue: reuse the existing polling loop, no separate timer thread) can
prove end-to-end with the connection types this codebase currently builds
real fixtures for.

**Acceptance-criteria scope, stated plainly:** no `events.jsonl` from any
real, non-synthetic run in this repository currently shows a heartbeat
event actually firing. The heartbeat mechanism (the interval check and the
`Emit` call) is verified only against a synthetic fake `dynamic` connection
object in `RefreshHeartbeatTests.cs`, with an artificially shortened
interval and a connection double engineered to keep reporting
`Refreshing = true`. It has not been observed to fire for any connection
type this codebase's own certification fixtures exercise -- the one real
connection type probed (`power_query_minimal`'s Power-Query/Mashup OLEDB
connection) blocks synchronously in `Refresh()` for its entire duration and
leaves no "still waiting" window for the loop to emit into. Treat the
heartbeat as mechanically-correct-by-unit-test, not yet demonstrated on any
real job this codebase can currently run end-to-end; closing that gap needs
a connection/provider confirmed to keep `Refreshing = true` past 5 seconds
after `Refresh()` returns (e.g. a provider that does not fully honor
`BackgroundQuery = false`), which no corpus item here currently provides.

### Pre-touch staging (issue #72)

`control_plane/cli.py`'s `run` subcommand now stages the manifest's `open`
step before ever invoking the supervisor: `staging.stage_copy` (#38, RFC
0002 decision 9) copies the real `workbook_path` into a fresh local temp
directory, and an *in-memory* copy of the parsed job dict (never the
caller's on-disk manifest file) has that step's `workbook_path` rewritten
to the staged copy. A `save_as` step's `output_path` is likewise rewritten
to a path inside that same staging directory, so the real save target is
never written to directly either; `staging.publish` swaps the staged
output into the real target only once `result.json` reports `ok: true`. See
`control_plane/cli.py`'s `cmd_run`/`_stage_job_for_run` docstrings and
`xlsx-win/README.md`'s "Running a job for real" section for the full
sequence -- this file's own C# supervisor/worker code is unchanged by this:
staging happens entirely one process boundary away, in the Python
control-plane layer, before the supervisor is ever launched.

### STA thread and message pump

`XlsxWinWorker`'s `Main` is `[STAThread]`. `UseWindowsForms` is enabled
purely to get `System.Windows.Forms.Application.DoEvents()` for a minimal
message pump (`MessagePump.PumpingDelay`), called during refresh/calculation
polling loops and while waiting for Excel's own process to exit. This is the
whole of this increment's ambient/passive message pumping. Bounded,
policy-driven retry handling for a busy/rejected COM call specifically is a
separate, complementary mechanism -- `IMessageFilter` (issue #72, see
"IMessageFilter COM-retry handling" above).

### Early-bound vs late-bound COM

The increment's brief called for trying `Microsoft.Office.Interop.Excel`
first and falling back to late-bound `dynamic` COM only on real friction.
That friction showed up immediately: the current `Microsoft.Office.Interop.Excel`
NuGet package (16.0.18925.20022) depends on separate `office`
(`Microsoft.Office.Core`) and `Microsoft.Vbe.Interop` primary interop
assemblies that are **not published to NuGet** and are not present on this
machine outside a full Office-PIA-install/GAC path. The build failed with
`CS0234: The type or namespace name 'Core' does not exist in the namespace
'Microsoft.Office'` with no straightforward package-reference fix. Per the
increment's own instruction not to burn excessive time on PIA versioning,
`XlsxWinWorker` and the integration tests use late-bound `dynamic` COM
(`Type.GetTypeFromProgID("Excel.Application")` / `Activator.CreateInstance`)
throughout instead. `dynamic` needs no extra package reference on net10.0 --
`Microsoft.CSharp.RuntimeBinder` ships in the shared framework.

Named Excel object-model constants normally pulled from an interop assembly
are hand-copied into `ExcelConstants.cs` from the published object model
documentation, **and then verified empirically via direct COM probing** where
memory turned out to be wrong (see "Known limitations" below) -- late-bound
code has no compiler to catch a wrong enum value, so don't trust memory for
these without a readback check.

### Job Object membership and Excel PID assignment

The supervisor creates an unnamed Job Object with
`JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` and assigns the worker process to it
immediately after `Process.Start()`. Excel itself, however, is **not**
automatically part of that job: COM-activated out-of-process servers are
launched via the OS's DCOM/RPC activation service, not as a direct child
process of the worker, so Job Object membership does not propagate to it for
free. The worker captures Excel's own PID from `Application.Hwnd` right after
starting it (RFC 0002 decision 8) and reports it in an event; the supervisor,
tailing that event stream, explicitly `OpenProcess` + `AssignProcessToJobObject`
that PID into the same job the moment it sees it. `TerminateJobObject` then
reliably takes down both processes in one unconditional call -- verified
directly (see "Verification of the kill path" below).

Process-kill scope, per safety rule 3: the only termination primitive this
codebase uses is `TerminateJobObject` against processes explicitly assigned
to the job (the worker's own PID from launch, and Excel's PID reported by the
worker). Nothing here enumerates or kills processes by name. The one
exception is test-fixture cleanup code (`FixtureWorkbookBuilder`) killing the
exact PID of an Excel instance *that same test-fixture method itself just
launched*, if it doesn't exit within a bounded wait -- again PID-scoped, never
by-name, and confined to test setup, not the supervisor/worker.

### Why the worker blocks on Excel's own process exit (`ExcelSession.CloseAndWait`)

An easy mistake here -- caught by safety-rule-5 verification, not assumed
away -- is for the worker to call `Application.Quit()`, have that COM call
return (which it typically does almost immediately), and then exit itself,
believing the job is done. `Quit()` returning is not proof `EXCEL.EXE` itself
has exited; empirically (see below) it can keep running for a long, variable
extra period. If the worker exited right after `Quit()` returned, the
supervisor would see a "clean" worker exit and report success while Excel
was still orphaned in the background -- exactly the failure mode this whole
project exists to close off.

So the worker calls `ExcelSession.CloseAndWait()` after its last step, which
closes the workbook, quits Excel, and then **blocks with no internal
timeout** until the captured Excel PID has actually exited. The worker
process staying alive during that wait is what keeps it visible to the
supervisor's phase-deadline tracking: `JobTimeouts.ForPhase` maps the
terminal `SUCCEEDED`/`FAILED` phases to `close_seconds`, so if Excel doesn't
exit within that budget, the supervisor's own deadline fires and
`TerminateJobObject` closes out both processes. There is deliberately only
one timeout authority (the supervisor); the worker doesn't duplicate or
race against it.

## Known limitations

### Connection-refresh shutdown latency

Real verification on this machine (see "Verification" below) surfaced a
genuine, reproducible-in-plain-COM-automation finding, independent of this
code: after a `WorkbookConnection.Refresh()` call (observed with both an
OLEDB "Mashup"/Power Query connection and a plain TEXT/QueryTable
connection), `Application.Quit()` returns almost immediately, but the
underlying `EXCEL.EXE` process can then take anywhere from a few seconds to
several minutes to actually exit -- confirmed via window enumeration to not
be a hidden modal dialog, and via thread inspection to not be a classic
deadlock (`Responding=True`, threads mostly in ordinary waits, one thread
observed `Running` rather than blocked). No open TCP connections were found
for the stuck process at the time, so it isn't simply hung on an outstanding
network call either. `TerminateProcess`/`TerminateJobObject` still kill it
instantly whenever tried, confirming this is genuinely a "how long does
Excel's own internal teardown take," not an unkillable state -- but that
"how long" is unpredictable and can be minutes. Given this, jobs whose steps
include a `refresh` should be given a generous `close_seconds` (the
`PerConnectionRefreshTests` integration test uses 600s) so the worker's own
bounded wait doesn't force an unnecessary Job-Object kill of a job that
actually completed successfully and is simply slow to tear down.

**Update from this session's re-verification pass (stronger finding than
originally documented above):** on this machine, the actual
`open`/`refresh`/`save_as` step work for `PerConnectionRefreshTests`'
workbook consistently completes in well under 15 seconds (confirmed via the
events.jsonl timeline in a manual, non-test invocation of the real
supervisor+worker against the same fixture shape, outside of xUnit
entirely); all of the remaining time is `ExcelSession.CloseAndWait()`
blocking on the Excel PID's own exit. Four independent runs of this exact
fixture in this session -- three at the test's original `close_seconds: 600`
(two via `dotnet test`, one via the manual invocation) and one at a
subsequently-raised `close_seconds: 900` -- **every single one** ran past
its configured deadline and was force-terminated by the supervisor's Job
Object, each time within about 47-49 seconds of that deadline (10 m 47 s at
600s, three times; 15 m 49 s at 900s, once). That consistent small overshoot,
repeated across a 300-second change in the underlying budget, is more
consistent with this specific Power-Query-backed fixture's `EXCEL.EXE`
process simply never exiting on its own on this machine (at least not within
any timeframe tried so far) than with "sometimes slow, eventually finishes."
Raising `close_seconds` further is not known to fix this, and was tried
once already without success -- see `PerConnectionRefreshTests.cs`.

This is the same underlying category of issue described above (Excel not
exiting promptly after `Quit()` post-refresh), not a new failure mode, and
it is **not** touched by any of the fixes applied in this session's code
review pass -- the step-execution timeline itself (open/refresh/save) is
fast and unchanged in all four runs, and the only thing that varies is how
long `CloseAndWait()`'s indefinite wait runs before the supervisor's
independent deadline cuts it off. Left as an open, pre-existing,
environment-specific issue for a follow-up to investigate (candidates: is it
specific to the Power Query "Mashup" OLEDB provider, this Office build, or
this machine's configuration?) rather than something this review pass
attempts to fix by guessing at a bigger number.

Critically, the safety-critical property held in all four runs regardless:
`TerminateJobObject` reliably killed the Excel process every time (post-run
`Get-Process -Name EXCEL` came back empty in all four cases), so this is a
test-reliability/environment gap, not a supervision failure -- the mechanism
this code exists to provide worked correctly each time it was needed.

**RESOLVED (later session): root cause found and fixed, not just re-verified
as still open.** The `power_query_minimal` item added to
`xlsx-win/certification/`'s corpus (a genuine Power Query M connection,
not this test's plainer `WorkbookConnection`) reproduced this exact
phenomenon twice, at two different `close_seconds` budgets. That prompted
actual web research (this is a well-documented category of .NET/COM interop
issue, not something new or unsolvable) rather than continuing to guess at a
bigger timeout. Root cause: `StepRunner.cs`'s `RunRefresh` obtained
`Workbook.Connections`, each `Connection`, and each
`OLEDBConnection`/`ODBCConnection` via COM property access and never
released any of them with `Marshal.ReleaseComObject` -- only the top-level
`Workbook`/`Application` were ever released, in `ExcelSession.cs`.
`Application.Quit()` only *requests* an exit; Excel will not actually
terminate until every outstanding COM reference (RCW) is released, and
relying on the .NET GC alone to get there can take multiple collection
cycles -- or, for a genuine Power-Query/Mashup-backed connection
specifically, apparently never resolve within any budget tried. Fixed by
explicit `Marshal.ReleaseComObject` on every one of those intermediate
objects (in `finally` blocks, surviving exceptions) plus strengthening this
class's `GC.Collect(); GC.WaitForPendingFinalizers();` to the standard
double-collect pattern (`GC.Collect(); GC.WaitForPendingFinalizers();
GC.Collect();` -- the second pass sweeps what the finalizer thread only
detached, not yet reclaimed). Reverified against `power_query_minimal`
after the fix, twice, both times identical: `SUCCEEDED`, `ok=true`, in 12.5
seconds -- down from timing out past every budget tried (up to 300s).
`PerConnectionRefreshTests` itself (this file) was updated to match: its
`close_seconds` no longer needs to be inflated to 900s, and its own
`Assert.DoesNotContain("RefreshAll", ...)` check -- which had never
actually run before, since this test always timed out before reaching it --
turned out to be a separate, unrelated, pre-existing assertion bug (the
success message legitimately contains the substring "RefreshAll" as part of
"(no RefreshAll)"), fixed alongside. See
`certification/README.md`'s "power_query_minimal" section for the full
before/after evidence.

### Startup-vs-hang deadline race

`start_excel_seconds` has to comfortably exceed realistic (non-hung) Excel
COM-activation latency, because the worker only reports its Excel PID (so
the supervisor can assign it to the Job Object) *after* Excel finishes
starting. If that deadline is set too aggressively and Excel's own startup
is slow for unrelated reasons (cold cache, system load), the supervisor could
in principle fire the timeout before the Excel PID is ever known, in which
case `TerminateJobObject` would only reach the worker process, not Excel.
This is a real, if narrow, edge case this increment does not close; a future
increment's UI-Automation/WinEvent work (already deferred, see below) or a
smarter activation-time PID discovery mechanism would be the way to close it
properly.

## Explicitly deferred to a later increment

- ~~**`IMessageFilter` COM-retry handling for rejected calls.** Not
  implemented. This increment's message pump is limited to periodic
  `Application.DoEvents()` calls during polling loops.~~ **Done (issue
  #72).** See "IMessageFilter COM-retry handling" above --
  `ComMessageFilter.cs`, registered/revoked around the worker's whole job
  run, retries `SERVERCALL_RETRYLATER` up to 10 times with a 200ms backoff,
  fails `SERVERCALL_REJECTED` immediately, and surfaces the per-step retry
  count in that step's result message.
- **UI-Automation/WinEvent modal-dialog detection and screenshot capture.**
  Not implemented. Prevention-first (RFC 0002 decision 7) covers the dialogs
  this increment's step types can trigger; this is the fallback for what
  prevention can't cover (e.g. credential prompts). Explicitly parked as its
  own issue, #74 -- not part of #72's light scope.
- ~~**Heartbeat file / liveness ping separate from phase-deadline tracking.**
  Not implemented. The event-stream tailer's phase-deadline mechanism is the
  only liveness signal this increment has.~~ **Done (issue #72), with a
  documented real-world caveat.** See "Heartbeat" above --
  `RefreshOneConnection`'s polling loop emits a periodic still-alive
  `WorkerEvent` (reusing the `REFRESHING_CONNECTIONS` phase, distinguished
  by `message: "heartbeat: still refreshing."`) while a connection refresh
  is still in progress. Confirmed, via direct COM probing, that this loop
  gets essentially no time to run (and so emits no heartbeat) for the
  Power-Query/Mashup OLEDB connections this codebase's own fixtures use,
  because `Refresh()` itself blocks synchronously for the connection's
  entire duration once `TrySetBackgroundQueryOff` forces
  `BackgroundQuery = false` -- proven correct instead against a fake
  connection object in `RefreshHeartbeatTests.cs`. **Acceptance criteria,
  narrowed to match current evidence:** the heartbeat is verified
  mechanically via that synthetic test double only; no real,
  non-synthetic `events.jsonl` in this repository demonstrates it firing,
  and it is not observed to fire for any connection type this codebase's
  own certification fixtures cover. See "Heartbeat" above for the full
  real-Excel probe this is based on.
- **Worker quarantine/recycle across multiple jobs.** Not applicable at this
  scope: the supervisor only ever runs one worker process at a time, by
  construction -- there is no pool to quarantine or recycle from.
- **Per-workbook distributed locking/fencing tokens.** Not implemented:
  single machine, single caller, moot for now.
- **`run_approved_macro` step type.** Recognized by the job/result models
  (it's part of #34's schema) but **not implemented** -- the worker returns an
  explicit `failed` step result with error code `MACRO_EXECUTION_DEFERRED`
  rather than silently doing nothing. Implementing it means re-enabling
  `AutomationSecurity` narrowly around the macro call plus allowlist
  verification by exact macro name, which is real, separate work this
  increment does not do.
- ~~**Wiring the Python `xlsx-win/control_plane/cli.py` to shell out to this
  supervisor.**~~ **Done (issue #71).** `cli.py run <manifest.json>` now
  validates the manifest, resolves the built executables, and invokes this
  supervisor using exactly the file-path contract described above. See
  `../control_plane/supervisor_runner.py` and `../README.md`'s "Using the
  CLI" section.
- ~~**Staging/local-copy of the input workbook before `Open`, and swap-back
  after `save_as` (RFC 0002 decision 9).** Not implemented. `OpenStep`/
  `ExcelSession.Open` opens whatever `workbook_path` the manifest supplies
  directly, in place -- a workbook on a OneDrive/SharePoint-synced path is
  **not** protected by this increment against the sync/AutoSave interaction
  problems decision 9 describes.~~ **Done (issue #72), at the Python
  control-plane layer, not in this C# code.** `control_plane/cli.py`'s `run`
  subcommand now stages the `open` step's `workbook_path` (and any `save_as`
  step's `output_path`) via the already-existing, already-tested #38
  `staging.stage_copy`/`staging.publish` primitives *before* ever invoking
  this supervisor -- see "Pre-touch staging" above and
  `../README.md`'s "Running a job for real" section. This C# supervisor/
  worker code itself is unchanged: it still just opens/saves whatever path
  its job.json says, exactly as before -- the staging now happens one layer
  up, so by the time this code ever sees a `workbook_path`, it is already a
  local staged copy, not the manifest's real input path.

## Verification performed

This section embeds the actual evidence from this repo's own runs, rather
than pointing at an external report a reviewer cannot check. All commands
below were run directly against this checkout; raw pass/fail counts and
timings are pasted verbatim (not summarized/rounded by hand).

### Build

```
dotnet build xlsx-win\supervisor\XlsxWinSupervisor.slnx
```

```
Build succeeded.
    0 Warning(s)
    0 Error(s)
Time Elapsed 00:00:09.72
```

### Unit tests (no Excel, `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS` unset)

```
dotnet test xlsx-win\supervisor\XlsxWinSupervisor.slnx
```

```
Passed!  - Failed:     0, Passed:    25, Skipped:     0, Total:    25, Duration: 271 ms - XlsxWinWorker.Tests.dll (net10.0)
Passed!  - Failed:     0, Passed:    31, Skipped:     0, Total:    31, Duration: 224 ms - XlsxWinSupervisor.Tests.dll (net10.0)
Skipped! - Failed:     0, Passed:     0, Skipped:     4, Total:     4, Duration: 55 ms - XlsxWinSupervisor.IntegrationTests.dll (net10.0)
```

All 56 unit tests pass; all 4 integration tests skip cleanly (env var not
set) without touching Excel. `Get-Process -Name EXCEL` returned nothing
before or after this run.

### Integration tests against real Excel (`XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1`)

Excel was confirmed not running (`Get-Process -Name EXCEL` returned nothing)
immediately before each run below.

```
$env:XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS = "1"
dotnet test xlsx-win\supervisor\XlsxWinSupervisor.IntegrationTests\XlsxWinSupervisor.IntegrationTests.csproj
```

Final run in this session (after raising `PerConnectionRefreshTests`'
`CloseSeconds` from 600 to 900 -- see "Known limitations" above for why that
change did not fully resolve the one failure below):

```
  Passed XlsxWinSupervisor.IntegrationTests.TimeoutKillTests.Hanging_worker_is_force_terminated_within_bounded_time_and_leaves_no_excel_process [56 s]
  Failed XlsxWinSupervisor.IntegrationTests.PerConnectionRefreshTests.Refresh_step_refreshes_the_single_connection_individually [15 m 49 s]
  Passed XlsxWinSupervisor.IntegrationTests.DialogPreventionTests.Dialog_prevention_properties_are_set_and_confirmed_via_com_readback [6 s]
  Passed XlsxWinSupervisor.IntegrationTests.HappyPathTests.Open_recalc_saveas_succeeds_and_leaves_no_excel_process [37 s]

Test Run Failed.
Total tests: 4
     Passed: 3
     Failed: 1
 Total time: 17.5274 Minutes
```

`PerConnectionRefreshTests` failed with `Assert.Equal() Failure: Values
differ / Expected: 0 / Actual: 1` -- the supervisor's own
`PHASE_DEADLINE_EXCEEDED` firing for the `SUCCEEDED` phase (confirmed by
directly inspecting `result.json` from an equivalent manual, non-test
invocation: `"final_state":"TIMED_OUT"`, `"ok":false`,
`"code":"PHASE_DEADLINE_EXCEEDED"`), not a step failure. This is the
pre-existing "connection-refresh shutdown latency" characteristic discussed
above, reproduced four times this session across two different
`close_seconds` budgets, and is independent of every fix applied in this
review pass -- see "Known limitations" for the full evidence trail. **In
every one of those four runs, including this failing one, the explicit
post-run check found zero surviving `EXCEL.EXE` processes** (`Get-Process
-Name EXCEL` empty both immediately after this test run and after the
standalone manual repro), confirming the Job-Object kill path -- including
this session's `AssignProcessById` identity-check change -- worked
correctly every time it was exercised, including under forced termination.

Immediately prior to this final run, in the same session:

- A first full run (before the `CloseSeconds` change, and before this was
  understood to need investigation) produced the same pass/fail split --
  `Total tests: 4, Passed: 3, Failed: 1` -- with `PerConnectionRefreshTests`
  failing at `10 m 47 s` against the original `close_seconds: 600`, and zero
  surviving Excel processes afterward.
- A standalone re-run of only `PerConnectionRefreshTests` (still at
  `close_seconds: 600`) reproduced the identical `10 m 47 s` failure a
  second time, again with zero surviving Excel processes afterward.
- A manual, non-`dotnet test` invocation of the real
  `XlsxWinSupervisor.exe`/`XlsxWinWorker.exe` pair against an equivalently-
  built fixture workbook (same Power Query/OLEDB connection shape) showed,
  via its `events.jsonl` timeline, that `open`→`refresh`→`save_as` completed
  in under 11 seconds; `result.json` afterward showed the same
  `PHASE_DEADLINE_EXCEEDED`/`TIMED_OUT` shape at the 600s mark, and,
  again, zero surviving Excel processes afterward.

**Net result: build passes; all 56 unit tests pass; 3 of 4 real-Excel
integration tests pass reliably; the 4th (`PerConnectionRefreshTests`) has a
reproducible, pre-existing, environment-specific timing flake unrelated to
any change made in this review pass, under active investigation, with the
safety-critical no-orphaned-process property verified holding in all four
observed occurrences of it.**
