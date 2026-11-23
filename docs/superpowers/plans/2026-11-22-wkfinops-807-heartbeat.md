# WKFINOPS-807 Worker Heartbeat Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Emit a worker-originated five-second heartbeat during native Excel work so inactivity measures worker liveness, while existing absolute caps still terminate a hung job.

**Architecture:** Make the existing event writer safe for a worker thread plus one timer thread and expose its last emitted phase. A small worker-side timer emits the existing `WorkerEvent` shape; the supervisor continues to own inactivity and absolute deadlines with no schema or state-name change.

**Tech Stack:** C# / .NET 10, xUnit, existing JSONL worker events, Windows Excel integration tests.

**Spec:** `docs/superpowers/specs/2026-11-22-wkfinops-807-heartbeat-design.md`

## Global Constraints

- Heartbeat interval is five seconds in production; tests inject a shorter interval.
- Heartbeat uses the current phase and `message: "heartbeat: worker still running."`; no new phase or schema field.
- Heartbeat refreshes inactivity only. Whole-job and phase caps remain unchanged and authoritative.
- No `rows_done`, deadline ratio, >80% warning, patient data, production run, or global runtime overwrite; full telemetry is WKFINOPS-833.
- Work remains on `WKFINOPS-807-native-heartbeat`; commit subjects begin `WKFINOPS-807`.

## Review Focus

- A synchronous COM call blocks the STA thread: the timer must still emit; pin with the existing real hang integration test in Task 2.
- Timer disposal races an in-flight callback: no write may occur after disposal; pin in Task 1.
- A live but non-completing worker must still hit its absolute cap; pin in Task 2.
- Heartbeat failure must not be silently presented as healthy progress; pin the explicit failure path in Task 1.
- Existing refresh heartbeats and event parsing must remain compatible; run the complete native unit suite in Task 3.

---

### Task 1: Thread-safe event writer and worker heartbeat

**Files:**
- Modify: `xlsx-win/supervisor/XlsxWinContracts/WorkerEvent.cs`
- Create: `xlsx-win/supervisor/XlsxWinWorker/WorkerHeartbeat.cs`
- Test: `xlsx-win/supervisor/XlsxWinWorker.Tests/WorkerHeartbeatTests.cs`

**Interfaces:**
- `EventWriter.Emit(WorkerEvent evt)` remains the ordinary write path and becomes synchronized.
- `EventWriter.EmitHeartbeat(string runId)` selects the last emitted phase and writes the heartbeat under that same lock, so a stale phase cannot become a later transition.
- `WorkerHeartbeat(EventWriter events, string runId, TimeSpan? interval = null)` starts the timer; `IDisposable` stops it before writer disposal.

- [ ] **Step 1: Write failing heartbeat tests**

Create tests proving: a heartbeat with the current phase/message appears while a `ManualResetEventSlim` blocks the calling thread; concurrent ordinary events and heartbeat events all parse; a forced phase-A/phase-B interleaving never emits a delayed phase-A heartbeat after phase B; disposal stops later writes; a writer failure is surfaced to the heartbeat owner rather than silently marked as progress.

- [ ] **Step 2: Verify RED**

Run: `dotnet test xlsx-win/supervisor/XlsxWinWorker.Tests/XlsxWinWorker.Tests.csproj --filter WorkerHeartbeatTests`
Expected: FAIL because `WorkerHeartbeat`, synchronized writes, and atomic `EmitHeartbeat` do not exist.

- [ ] **Step 3: Implement the minimal synchronized writer and timer**

Lock `EventWriter.Emit`/phase update and make disposal mutually exclusive with writes. Implement `EventWriter.EmitHeartbeat` so phase selection and heartbeat emission are one atomic operation. Implement `WorkerHeartbeat` with `System.Threading.Timer`, an injectable interval, and deterministic callback/disposal coordination. Do not add fields to `WorkerEvent`.

- [ ] **Step 4: Verify GREEN**

Run the Step 2 command. Expected: all `WorkerHeartbeatTests` PASS.

- [ ] **Step 5: Commit**

Stage the three Task 1 files explicitly and commit `WKFINOPS-807 Add a thread-safe worker heartbeat`.

### Task 2: Start heartbeat and prove the real blocked-worker behavior

**Files:**
- Modify: `xlsx-win/supervisor/XlsxWinWorker/Program.cs`
- Test: `xlsx-win/supervisor/XlsxWinSupervisor.IntegrationTests/TimeoutKillTests.cs`

**Interfaces:**
- Consumes Task 1's `WorkerHeartbeat(EventWriter, string, TimeSpan?)` and atomic `EventWriter.EmitHeartbeat(string)`.
- Produces heartbeat events throughout `RunJob`, including composite preflight and the existing test-only synchronous hang.

- [ ] **Step 1: Add failing real-hang assertions**

In the existing opt-in timeout-kill test, require at least one worker heartbeat while the STA thread is blocked. Set inactivity below the observed hang window but above the heartbeat interval, then use explicit phase/whole-job budgets that independently identify the expected absolute kill. Assert `TIMED_OUT`, the failed supervisor step's exact `ABSOLUTE_DEADLINE_EXCEEDED` code, the expected absolute/phase reason, elapsed bound, and process cleanup. Add the same-phase supervisor acceptance case in `TimeoutKillTests.cs`, proving activity refreshes inactivity while phase-start and whole-job-start timestamps remain unchanged through the real supervisor event loop rather than duplicated deadline arithmetic.

- [ ] **Step 2: Verify RED**

Run `dotnet test xlsx-win/supervisor/XlsxWinSupervisor.IntegrationTests/XlsxWinSupervisor.IntegrationTests.csproj --filter FullyQualifiedName~TimeoutKillTests` with `XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1`, only when its existing no-other-Excel gate passes. This executes both the pre-existing real-hang case and the new same-phase acceptance case. Expected: the new heartbeat assertion FAILs because `RunJob` has no heartbeat; do not weaken the pre-existing timeout assertion.

- [ ] **Step 3: Wire one heartbeat into `RunJob`**

Immediately after the initial `STARTING_EXCEL` event, create one `WorkerHeartbeat` with the default five-second interval. Use deterministic disposal for every return/exception path. Leave `MaybeSimulateHang`, `StepRunner`, and supervisor deadline code unchanged.

- [ ] **Step 4: Verify GREEN**

Run the same `FullyQualifiedName~TimeoutKillTests` class against the new build, requiring separate phase-cap and whole-job-cap outcomes, then Task 1's tests. Expected: heartbeat observed, each absolute-cap timeout and cleanup green, and all heartbeat unit tests PASS.

- [ ] **Step 5: Commit**

Stage the two Task 2 files explicitly and commit `WKFINOPS-807 Emit heartbeat without defeating the absolute cap`.

### Task 3: Document and validate the native build

**Files:**
- Modify: `xlsx-win/supervisor/README.md`

**Interfaces:**
- Documents the Task 2 production heartbeat and the existing `XLSXWIN_TEST_SIMULATE_HANG_SECONDS` proof.

- [ ] **Step 1: Run the complete no-Excel native suite**

Run `dotnet test xlsx-win/supervisor/XlsxWinSupervisor.slnx` without the integration gate. Expected: all ordinary unit tests PASS and integration tests skip by their existing gate.

- [ ] **Step 2: Update the heartbeat documentation**

Document worker-originated timer semantics, the five-second interval, inactivity versus absolute caps, and the explicit exclusion of rows/deadline-ratio telemetry. Replace both stale claims: that coverage exists only for refresh polling, and that same-phase heartbeat resets the supervisor's phase-deadline clock. Phase start and whole-job start remain unchanged by heartbeat.

- [ ] **Step 3: Commit and record the runtime-promotion boundary**

Stage `xlsx-win/supervisor/README.md` explicitly and commit `WKFINOPS-807 Document worker heartbeat and cap semantics`. Record the tested HEAD and native build/test evidence. Runtime pinning and fresh `-08` observation remain controlled delivery steps, not claims made by this local commit.
