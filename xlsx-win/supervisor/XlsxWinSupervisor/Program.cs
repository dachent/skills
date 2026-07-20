using System.Diagnostics;
using System.IO.Pipes;
using System.Security.Principal;
using XlsxWinContracts;

namespace XlsxWinSupervisor;

internal static class Program
{
    private const int PollIntervalMs = 200;

    private static int Main(string[] args)
    {
        SupervisorArgs parsedArgs;
        JobManifest manifest;
        try
        {
            parsedArgs = SupervisorArgs.Parse(args);
            manifest = JobManifest.Parse(File.ReadAllText(parsedArgs.JobPath));
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 2;
        }

        var timeouts = manifest.Timeouts ?? new JobTimeouts();
        var tracker = new DeadlineTracker(timeouts);
        EnsureParentDirectory(parsedArgs.EventsPath);
        EnsureParentDirectory(parsedArgs.ResultPath);
        File.WriteAllText(parsedArgs.EventsPath, string.Empty);
        File.WriteAllText(parsedArgs.ResultPath, string.Empty);

        string workerExePath;
        try { workerExePath = WorkerLauncher.ResolveWorkerExePath(); }
        catch (Exception ex) { Console.Error.WriteLine(ex.Message); return 2; }

        using var job = JobObjectHandle.Create();
        var pipeName = $"xlsx-win-control-{Guid.NewGuid():N}";
        using var controlPipe = new NamedPipeServerStream(
            pipeName, PipeDirection.InOut, 1, PipeTransmissionMode.Byte,
            PipeOptions.Asynchronous | PipeOptions.WriteThrough);
        using var suspended = SuspendedWorker.Create(workerExePath,
            new[] { parsedArgs.JobPath, parsedArgs.EventsPath, parsedArgs.ResultPath, pipeName });
        job.AssignProcess(suspended.ProcessHandle);
        using var worker = suspended.Resume();

        ExcelProcessIdentity identity;
        try
        {
            identity = CompleteContainmentHandshake(controlPipe, job, timeouts.StartExcelSeconds);
        }
        catch (Exception ex)
        {
            return HandleContainmentFailure(job, worker, manifest, parsedArgs.ResultPath, ex);
        }

        var startedUtc = DateTime.UtcNow;
        var currentPhase = "STARTING_EXCEL";
        var phaseStartedUtc = startedUtc;
        var lastActivityUtc = startedUtc;
        var lastSampleUtc = DateTime.MinValue;
        string? breachReason = null;

        using var tailer = new EventTailer(parsedArgs.EventsPath);
        using var telemetry = new TelemetrySampler(parsedArgs.EventsPath);
        telemetry.Sample(currentPhase, worker.Id, identity.ExcelPid, "containment_acknowledged");

        while (!worker.HasExited)
        {
            foreach (var evt in tailer.ReadNewEvents())
            {
                lastActivityUtc = DateTime.UtcNow;
                if (!string.IsNullOrEmpty(evt.Phase) && !string.Equals(evt.Phase, currentPhase, StringComparison.Ordinal))
                {
                    currentPhase = evt.Phase;
                    phaseStartedUtc = lastActivityUtc;
                    telemetry.Sample(currentPhase, worker.Id, identity.ExcelPid, "phase_boundary");
                }
            }

            if (worker.HasExited) break;
            var now = DateTime.UtcNow;
            if ((now - lastSampleUtc).TotalSeconds >= 1)
            {
                telemetry.Sample(currentPhase, worker.Id, identity.ExcelPid, "periodic");
                lastSampleUtc = now;
            }
            if ((now - startedUtc).TotalSeconds > timeouts.WholeJobSeconds)
                breachReason = $"whole-job deadline {timeouts.WholeJobSeconds}s exceeded";
            else if ((now - lastActivityUtc).TotalSeconds > timeouts.InactivitySeconds)
                breachReason = $"inactivity watchdog {timeouts.InactivitySeconds}s exceeded";
            else if (tracker.IsBreached(currentPhase, phaseStartedUtc, now))
                breachReason = $"phase '{currentPhase}' deadline {tracker.DeadlineSecondsFor(currentPhase)}s exceeded";
            if (breachReason is not null) break;
            Thread.Sleep(PollIntervalMs);
        }

        if (breachReason is not null)
            return HandleTimeout(job, worker, manifest, currentPhase, breachReason, parsedArgs.ResultPath, timeouts.ShutdownSeconds);
        return HandleCleanExit(job, worker, suspended.ExitCode, manifest, parsedArgs.ResultPath, timeouts.ShutdownSeconds);
    }

    private static ExcelProcessIdentity CompleteContainmentHandshake(
        NamedPipeServerStream pipe, JobObjectHandle job, int timeoutSeconds)
    {
        using var cancellation = new CancellationTokenSource(TimeSpan.FromSeconds(timeoutSeconds));
        pipe.WaitForConnectionAsync(cancellation.Token).GetAwaiter().GetResult();
        ExcelProcessIdentity? identity = null;
        try
        {
            identity = FramedControl.Read<ExcelProcessIdentity>(pipe);
            ValidateExcelIdentity(identity);
            job.AssignProcessById(identity.ExcelPid);
            FramedControl.Write(pipe, new ContainmentAck { Accepted = true, Message = "Exact Excel process assigned to Job Object." });
            return identity;
        }
        catch (Exception ex)
        {
            if (pipe.IsConnected)
            {
                try { FramedControl.Write(pipe, new ContainmentAck { Accepted = false, Message = ex.Message }); } catch { }
            }
            throw new InvalidOperationException($"Excel containment handshake failed: {ex.Message}", ex);
        }
    }

    private static void ValidateExcelIdentity(ExcelProcessIdentity identity)
    {
        using var process = Process.GetProcessById(identity.ExcelPid);
        var actualCreation = process.StartTime.ToUniversalTime().ToFileTimeUtc();
        var actualImage = process.MainModule?.FileName ?? "";
        var actualUser = WindowsIdentity.GetCurrent().Name;
        if (actualCreation != identity.CreationTimeUtcFileTime
            || process.SessionId != identity.SessionId
            || !string.Equals(Path.GetFullPath(actualImage), Path.GetFullPath(identity.ImagePath), StringComparison.OrdinalIgnoreCase)
            || !string.Equals(Path.GetFileName(actualImage), "EXCEL.EXE", StringComparison.OrdinalIgnoreCase)
            || !string.Equals(identity.User, actualUser, StringComparison.OrdinalIgnoreCase)
            || identity.Hwnd == 0)
            throw new InvalidOperationException("Excel PID/creation/image/session/user/Hwnd identity did not validate exactly.");
    }

    private static int HandleContainmentFailure(
        JobObjectHandle job, Process worker, JobManifest manifest, string resultPath, Exception exception)
    {
        var cleanup = TerminateAndVerify(job, worker, 5, out var cleanupDetail);
        var result = ResultDocument.Build(
            $"supervisor-containment-failed-{Guid.NewGuid():N}", manifest.IdempotencyKey, "FAILED",
            new List<StepResult> { SupervisorFailure("CONTAINMENT_HANDSHAKE_FAILED",
                $"Containment failed before workbook access: {exception.Message}; {cleanupDetail}", cleanup) },
            new List<InvariantResult> { CleanupInvariant(cleanup, cleanupDetail) });
        File.WriteAllText(resultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return 1;
    }

    private static int HandleTimeout(
        JobObjectHandle job, Process worker, JobManifest manifest, string phase, string reason,
        string resultPath, int shutdownSeconds)
    {
        var cleanup = TerminateAndVerify(job, worker, shutdownSeconds, out var cleanupDetail);
        var result = ResultDocument.Build(
            $"supervisor-timeout-{Guid.NewGuid():N}", manifest.IdempotencyKey, "TIMED_OUT",
            new List<StepResult> { SupervisorFailure("ABSOLUTE_DEADLINE_EXCEEDED",
                $"{reason}; phase={phase}; {cleanupDetail}", cleanup) },
            new List<InvariantResult> { CleanupInvariant(cleanup, cleanupDetail) });
        File.WriteAllText(resultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return 1;
    }

    private static bool TerminateAndVerify(
        JobObjectHandle job, Process worker, int shutdownSeconds, out string detail)
    {
        try
        {
            job.Terminate();
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(Math.Min(shutdownSeconds, 5));
            while (DateTime.UtcNow < deadline)
            {
                if (!worker.HasExited) worker.WaitForExit(100);
                if (job.ActiveProcessCount() == 0)
                {
                    detail = "termination_verified=true; owned_processes_zero=true";
                    return true;
                }
                Thread.Sleep(50);
            }
            detail = $"termination_verified=false; active_owned_processes={job.ActiveProcessCount()}";
            return false;
        }
        catch (Exception ex)
        {
            detail = $"termination_verified=false; error={ex.Message}";
            return false;
        }
    }

    internal static int HandleCleanExit(JobObjectHandle job, Process worker, int workerExitCode, JobManifest manifest, string resultPath, int shutdownSeconds)
    {
        string resultJson;
        try { resultJson = File.ReadAllText(resultPath); }
        catch (Exception ex) { return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds, ex.Message); }
        if (string.IsNullOrWhiteSpace(resultJson))
            return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds, "the result file was empty");
        ResultDocument result;
        try { result = ResultDocument.Parse(resultJson); }
        catch (Exception ex) { return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds, $"invalid result: {ex.Message}"); }

        var recomputed = ResultDocument.ComputeOk(result.Steps, result.Invariants);
        var consistent = result.SchemaVersion == "2.0"
            && result.Ok == recomputed
            && (result.FinalState == "SUCCEEDED") == recomputed
            && ((workerExitCode == 0) == recomputed);
        uint active;
        try { active = job.ActiveProcessCount(); }
        catch (Exception ex) { return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds, $"cleanup accounting failed: {ex.Message}"); }
        if (!consistent)
            return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds,
                $"result trust/cleanup check failed (computed_ok={recomputed}, producer_ok={result.Ok}, final_state={result.FinalState}, worker_exit={workerExitCode}, active_owned={active})");
        if (active != 0 && recomputed)
        {
            try { active = WaitForOwnedProcessesToExit(job, shutdownSeconds); }
            catch (Exception ex) { return WorkerExitedWithoutResult(job, worker, manifest, resultPath, shutdownSeconds, $"cleanup grace accounting failed: {ex.Message}"); }
        }
        if (active != 0)
            return HandleResidualOwnedProcesses(job, worker, result, resultPath, shutdownSeconds, active);
        var attestedInvariants = result.Invariants.ToList();
        attestedInvariants.Add(new InvariantResult
        {
            Name = "supervisor_owned_processes_zero",
            Passed = true,
            Message = "active_owned_processes=0",
        });
        var attested = ResultDocument.Build(
            result.RunId, result.IdempotencyKey, result.FinalState, result.Steps, attestedInvariants);
        File.WriteAllText(resultPath, attested.ToJson());
        Console.WriteLine(attested.ToJson());
        return TrustedResultExitCode(recomputed);
    }

    internal static int TrustedResultExitCode(bool resultOk) => resultOk ? 0 : 1;

    internal static uint WaitForOwnedProcessesToExit(JobObjectHandle job, int shutdownSeconds)
    {
        var timeout = TimeSpan.FromSeconds(Math.Max(0, shutdownSeconds));
        var stopwatch = Stopwatch.StartNew();
        var active = job.ActiveProcessCount();
        while (active != 0 && stopwatch.Elapsed < timeout)
        {
            var remaining = timeout - stopwatch.Elapsed;
            if (remaining <= TimeSpan.Zero) break;
            Thread.Sleep((int)Math.Min(PollIntervalMs, Math.Ceiling(remaining.TotalMilliseconds)));
            active = job.ActiveProcessCount();
        }
        return active;
    }


    private static int HandleResidualOwnedProcesses(
        JobObjectHandle job, Process worker, ResultDocument workerResult, string resultPath, int shutdownSeconds, uint active)
    {
        var cleanup = TerminateAndVerify(job, worker, shutdownSeconds, out var cleanupDetail);
        var result = BuildResidualCleanupResult(workerResult, active, cleanup, cleanupDetail);
        File.WriteAllText(resultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return TrustedResultExitCode(result.Ok);
    }

    internal static ResultDocument BuildResidualCleanupResult(
        ResultDocument workerResult, uint originalActive, bool cleanup, string cleanupDetail)
    {
        if (workerResult.Ok && cleanup)
        {
            var attestedInvariants = workerResult.Invariants.ToList();
            attestedInvariants.Add(new InvariantResult
            {
                Name = "supervisor_owned_processes_zero",
                Passed = true,
                Message = $"active_owned_processes=0; forced_residual_cleanup=true; " +
                    $"original_active_owned_processes={originalActive}; {cleanupDetail}",
            });
            return ResultDocument.Build(
                workerResult.RunId, workerResult.IdempotencyKey, "SUCCEEDED",
                workerResult.Steps, attestedInvariants);
        }

        var message = $"Worker result was trustworthy but {originalActive} owned process(es) remained; {cleanupDetail}";
        var steps = workerResult.Steps.ToList();
        steps.Add(SupervisorFailure("OWNED_PROCESS_CLEANUP_REQUIRED", message, cleanup));
        var invariants = workerResult.Invariants.ToList();
        invariants.Add(CleanupInvariant(cleanup, cleanupDetail));
        return ResultDocument.Build(workerResult.RunId, workerResult.IdempotencyKey, "FAILED", steps, invariants);
    }

    private static int WorkerExitedWithoutResult(JobObjectHandle job, Process worker, JobManifest manifest, string resultPath, int shutdownSeconds, string detail)
    {
        var cleanup = TerminateAndVerify(job, worker, shutdownSeconds, out var cleanupDetail);
        var message = $"{detail}; {cleanupDetail}";
        var result = ResultDocument.Build(
            $"supervisor-worker-untrusted-{Guid.NewGuid():N}", manifest.IdempotencyKey, "FAILED",
            new List<StepResult> { SupervisorFailure("WORKER_RESULT_UNTRUSTED", message, cleanup) },
            new List<InvariantResult> { CleanupInvariant(cleanup, cleanupDetail) });
        File.WriteAllText(resultPath, result.ToJson());
        Console.WriteLine(result.ToJson());
        return 1;
    }

    private static InvariantResult CleanupInvariant(bool cleanup, string detail) => new()
    {
        Name = "supervisor_owned_process_cleanup",
        Passed = cleanup,
        Message = detail,
    };

    private static StepResult SupervisorFailure(string code, string message, bool cleanup) => new()
    {
        StepIndex = -1,
        Type = "supervisor",
        Status = "failed",
        Message = message,
        Error = new ErrorDetail
        {
            Code = code,
            Message = message,
            Details = new Dictionary<string, object?> { ["cleanup_verified"] = cleanup },
        },
    };

    private static void EnsureParentDirectory(string path)
    {
        var directory = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(directory)) Directory.CreateDirectory(directory);
    }
}
