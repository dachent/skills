using XlsxWinContracts;

namespace XlsxWinWorker;

internal static class Program
{
    // Test-only hang simulation, per issue #36 increment 1 scope: makes the
    // worker's STA thread block for longer than a configured deadline so the
    // supervisor's Job-Object kill path can be proven deterministically
    // against a genuinely unresponsive worker+Excel pair, without depending
    // on a flaky slow external data source. Never read outside test runs; a
    // production job manifest has no way to set this.
    private const string SimulateHangEnvVar = "XLSXWIN_TEST_SIMULATE_HANG_SECONDS";

    // Test-only crash simulation, per issue #39: makes the worker throw a
    // genuinely unhandled exception after completing exactly N steps but
    // before the final result.json is ever written, so the supervisor's
    // "worker exited without a trustworthy result" handling (Program.cs
    // WorkerExitedWithoutResult, added for the #36 review's blocker finding)
    // can be proven through a real end-to-end supervisor invocation, not just
    // a unit test. Never read outside test runs; a production job manifest
    // has no way to set this.
    private const string SimulateCrashEnvVar = "XLSXWIN_TEST_SIMULATE_CRASH_AFTER_STEP";

    [STAThread]
    private static int Main(string[] args)
    {
        WorkerArgs parsedArgs;
        try
        {
            parsedArgs = WorkerArgs.Parse(args);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 2;
        }

        var runId = Guid.NewGuid().ToString("N");
        var stepResults = new List<StepResult>();

        using var events = new EventWriter(parsedArgs.EventsPath);

        JobManifest manifest;
        try
        {
            var jobJson = File.ReadAllText(parsedArgs.JobPath);
            manifest = JobManifest.Parse(jobJson);
        }
        catch (Exception ex)
        {
            return WriteFailureAndExit(events, runId, "unknown", parsedArgs.ResultPath, stepResults,
                $"Failed to read/parse job manifest at '{parsedArgs.JobPath}': {ex.Message}");
        }

        var timeouts = manifest.Timeouts ?? new JobTimeouts();

        // Registered immediately after the manifest is known to parse, before
        // Excel is ever started, and revoked unconditionally on every exit
        // path from here on (including exceptions) via the try/finally below.
        // See ComMessageFilter's doc comment for the retry policy this
        // installs on the worker's own STA apartment.
        ComMessageFilter.Register();
        try
        {
            return RunJob(parsedArgs, runId, stepResults, events, manifest, timeouts);
        }
        finally
        {
            ComMessageFilter.Revoke();
        }
    }

    private static int RunJob(
        WorkerArgs parsedArgs,
        string runId,
        List<StepResult> stepResults,
        EventWriter events,
        JobManifest manifest,
        JobTimeouts timeouts)
    {
        events.Emit(new WorkerEvent { RunId = runId, Phase = "STARTING_EXCEL" });

        using var session = new ExcelSession();
        try
        {
            var excelPid = session.Start();
            events.Emit(new WorkerEvent
            {
                RunId = runId,
                Phase = "STARTING_EXCEL",
                ExcelPid = excelPid,
                Message = "Excel started; dialog-prevention properties applied.",
            });
        }
        catch (Exception ex)
        {
            return WriteFailureAndExit(events, runId, manifest.IdempotencyKey, parsedArgs.ResultPath, stepResults,
                $"Failed to start Excel: {ex.Message}");
        }

        try
        {
            var identity = ContainmentClient.ConnectAndAwaitAcknowledgement(
                parsedArgs.ControlPipeName,
                session,
                TimeSpan.FromSeconds(timeouts.StartExcelSeconds));
            events.Emit(new WorkerEvent
            {
                RunId = runId,
                Phase = "STARTING_EXCEL",
                ExcelPid = identity.ExcelPid,
                Message = "Supervisor acknowledged exact Excel identity and Job Object containment; workbook access is now enabled.",
            });
        }
        catch (Exception ex)
        {
            return WriteFailureAndExit(events, runId, manifest.IdempotencyKey, parsedArgs.ResultPath, stepResults,
                $"Excel containment acknowledgement failed before workbook access: {ex.Message}");
        }

        MaybeSimulateHang(events, runId);

        var runner = new StepRunner(session, events, runId, timeouts);
        var anyFailed = false;
        for (var i = 0; i < manifest.Steps.Count; i++)
        {
            if (anyFailed)
            {
                stepResults.Add(new StepResult
                {
                    StepIndex = i,
                    Type = manifest.Steps[i].GetType().Name,
                    Status = "skipped",
                    Message = "Skipped after an earlier step failed.",
                });
                continue;
            }

            var stepResult = runner.Run(i, manifest.Steps[i]);
            stepResults.Add(stepResult);
            if (stepResult.Status != "succeeded")
            {
                anyFailed = true;
            }

            MaybeSimulateCrashAfterStep(events, runId, completedStepCount: i + 1);
        }

        var finalState = anyFailed ? "FAILED" : "SUCCEEDED";
        events.Emit(new WorkerEvent { RunId = runId, Phase = finalState });

        // Blocks until Excel's own process has actually exited -- not just
        // until Quit() returns, which can happen well before EXCEL.EXE is
        // really gone (see ExcelSession.CloseAndWait doc comment). Keeping
        // this worker process alive for that whole wait is what lets the
        // supervisor's phase-deadline enforcement (close_seconds, mapped to
        // this terminal phase) remain the actual authority on how long that's
        // allowed to take, with its Job Object kill as the backstop.
        session.CloseAndWait();

        var leaseBalancePassed = session.Gateway.TrackedOwnedRcwLeases == 0;
        var leaseEvidence =
            $"tracked_owned_rcw_leases={session.Gateway.TrackedOwnedRcwLeases}; " +
            $"tracked_owned_rcw_high_water={session.Gateway.TrackedOwnedRcwHighWater}";
        var invariants = new List<InvariantResult>
        {
            new()
            {
                Name = "tracked_owned_rcw_lease_balance",
                Passed = leaseBalancePassed,
                Message = leaseEvidence,
            },
        };
        if (!leaseBalancePassed)
        {
            finalState = "FAILED";
            events.Emit(new WorkerEvent { RunId = runId, Phase = finalState, Message = leaseEvidence });
        }
        var result = ResultDocument.Build(runId, manifest.IdempotencyKey, finalState, stepResults, invariants);
        File.WriteAllText(parsedArgs.ResultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return result.Ok && finalState == "SUCCEEDED" ? 0 : 1;
    }

    private static int WriteFailureAndExit(
        EventWriter events,
        string runId,
        string idempotencyKey,
        string resultPath,
        List<StepResult> stepResults,
        string message)
    {
        events.Emit(new WorkerEvent { RunId = runId, Phase = "FAILED", Message = message });
        var result = ResultDocument.Build(runId, idempotencyKey, "FAILED", stepResults);
        File.WriteAllText(resultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return 1;
    }

    private static void MaybeSimulateHang(EventWriter events, string runId)
    {
        var raw = Environment.GetEnvironmentVariable(SimulateHangEnvVar);
        if (string.IsNullOrWhiteSpace(raw) || !int.TryParse(raw, out var seconds) || seconds <= 0)
        {
            return;
        }

        events.Emit(new WorkerEvent
        {
            RunId = runId,
            Phase = "STARTING_EXCEL",
            Message = $"{SimulateHangEnvVar}={seconds}: blocking the STA thread to simulate a hang (test-only).",
        });

        // Deliberately a plain, non-pumping sleep: this simulates the worker's
        // STA thread being wedged inside a synchronous COM call that never
        // returns, which is exactly the scenario cooperative shutdown cannot
        // recover from and only the supervisor's Job Object can terminate.
        Thread.Sleep(TimeSpan.FromSeconds(seconds));
    }

    private static void MaybeSimulateCrashAfterStep(EventWriter events, string runId, int completedStepCount)
    {
        var raw = Environment.GetEnvironmentVariable(SimulateCrashEnvVar);
        if (string.IsNullOrWhiteSpace(raw) || !int.TryParse(raw, out var crashAfter) || crashAfter <= 0)
        {
            return;
        }

        if (completedStepCount != crashAfter)
        {
            return;
        }

        events.Emit(new WorkerEvent
        {
            RunId = runId,
            Phase = "APPLYING_EDITS",
            Message = $"{SimulateCrashEnvVar}={crashAfter}: about to simulate an unhandled worker " +
                      "crash (test-only) after completing this many steps, before this run's " +
                      "result.json is written.",
        });

        // Suppress the OS's "program has stopped working" crash dialog (and
        // any registered JIT debugger prompt) for this process before
        // throwing -- see NativeMethods.SetErrorMode's doc comment. Without
        // this, a genuinely unhandled exception here could in principle
        // surface blocking UI on a real, actively-used desktop, which the
        // safety rules for this issue explicitly rule out risking.
        NativeMethods.SetErrorMode(NativeMethods.SemFailCriticalErrors | NativeMethods.SemNoGpFaultErrorBox);

        throw new InvalidOperationException(
            $"{SimulateCrashEnvVar}={crashAfter}: simulated unhandled worker crash (test-only), " +
            "deliberately thrown before this run's result.json is written. If the supervisor " +
            "reports this run as a stale/prior success rather than a failure, that is the exact " +
            "regression this test exists to catch.");
    }
}
