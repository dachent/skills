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

        var result = ResultDocument.Build(runId, manifest.IdempotencyKey, finalState, stepResults);
        File.WriteAllText(parsedArgs.ResultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return finalState == "SUCCEEDED" ? 0 : 1;
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
}
