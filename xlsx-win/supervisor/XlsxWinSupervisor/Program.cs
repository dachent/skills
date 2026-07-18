using System.Diagnostics;
using XlsxWinContracts;

namespace XlsxWinSupervisor;

internal static class Program
{
    private const int PollIntervalMs = 200;

    private static int Main(string[] args)
    {
        SupervisorArgs parsedArgs;
        try
        {
            parsedArgs = SupervisorArgs.Parse(args);
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 2;
        }

        JobManifest manifest;
        try
        {
            manifest = JobManifest.Parse(File.ReadAllText(parsedArgs.JobPath));
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine($"Failed to read/parse job manifest at '{parsedArgs.JobPath}': {ex.Message}");
            return 2;
        }

        var timeouts = manifest.Timeouts ?? new JobTimeouts();
        var tracker = new DeadlineTracker(timeouts);

        EnsureParentDirectory(parsedArgs.EventsPath);
        EnsureParentDirectory(parsedArgs.ResultPath);
        // Truncate any stale events/result files from a previous run at these
        // paths. Truncating resultPath specifically closes off the "worker
        // dies before writing its own result.json, and a stale SUCCEEDED
        // document from an earlier run at the same path gets echoed as this
        // run's outcome" failure mode -- realistic whenever a caller reuses a
        // per-job directory across retries/re-runs. See HandleCleanExit,
        // which additionally refuses to trust an empty/unparseable file.
        File.WriteAllText(parsedArgs.EventsPath, string.Empty);
        File.WriteAllText(parsedArgs.ResultPath, string.Empty);

        string workerExePath;
        try
        {
            workerExePath = WorkerLauncher.ResolveWorkerExePath();
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine(ex.Message);
            return 2;
        }

        using var job = JobObjectHandle.Create();

        var startInfo = new ProcessStartInfo
        {
            FileName = workerExePath,
            UseShellExecute = false,
        };
        startInfo.ArgumentList.Add(parsedArgs.JobPath);
        startInfo.ArgumentList.Add(parsedArgs.EventsPath);
        startInfo.ArgumentList.Add(parsedArgs.ResultPath);

        using var worker = Process.Start(startInfo)
            ?? throw new InvalidOperationException($"Failed to start worker process '{workerExePath}'.");

        // Assign the worker process to the Job Object immediately after
        // launch -- this is what makes TerminateJobObject reliable later even
        // if the worker's STA thread never responds again.
        job.AssignProcess(worker.Handle);

        var startedUtc = DateTime.UtcNow;
        var currentPhase = "STARTING_EXCEL";
        var lastTransitionUtc = startedUtc;
        var excelPidAssigned = false;

        using var tailer = new EventTailer(parsedArgs.EventsPath);

        var timedOut = false;
        while (!worker.HasExited)
        {
            foreach (var evt in tailer.ReadNewEvents())
            {
                if (!string.IsNullOrEmpty(evt.Phase))
                {
                    currentPhase = evt.Phase;
                    lastTransitionUtc = DateTime.UtcNow;
                }

                if (evt.ExcelPid is { } excelPid && !excelPidAssigned)
                {
                    try
                    {
                        job.AssignProcessById(excelPid);
                        excelPidAssigned = true;
                    }
                    catch (Exception ex)
                    {
                        Console.Error.WriteLine(
                            $"Warning: failed to assign Excel PID {excelPid} to the Job Object: {ex.Message}. " +
                            "Force-termination may not reliably reach Excel if this worker later hangs.");
                    }
                }
            }

            if (worker.HasExited)
            {
                break;
            }

            if (tracker.IsBreached(currentPhase, lastTransitionUtc, DateTime.UtcNow))
            {
                timedOut = true;
                break;
            }

            Thread.Sleep(PollIntervalMs);
        }

        if (timedOut)
        {
            return HandleTimeout(job, worker, manifest, currentPhase, parsedArgs.ResultPath);
        }

        return HandleCleanExit(worker, manifest, parsedArgs.ResultPath);
    }

    private static int HandleTimeout(
        JobObjectHandle job,
        Process worker,
        JobManifest manifest,
        string currentPhase,
        string resultPath)
    {
        // Unconditional: kills the worker process AND the Excel process it
        // owns (once its PID has been assigned to this job), in one call,
        // without requiring either to cooperate.
        job.Terminate();
        worker.WaitForExit(5000);

        var deadlineSeconds = new DeadlineTracker(manifest.Timeouts ?? new JobTimeouts()).DeadlineSecondsFor(currentPhase);
        var timeoutResult = ResultDocument.Build(
            runId: $"supervisor-timeout-{Guid.NewGuid():N}",
            idempotencyKey: manifest.IdempotencyKey,
            finalState: "TIMED_OUT",
            steps: new List<StepResult>
            {
                new()
                {
                    StepIndex = -1,
                    Type = "supervisor",
                    Status = "failed",
                    Message = $"Phase '{currentPhase}' exceeded its {deadlineSeconds}s deadline; " +
                              "Job Object terminated the worker and its Excel process.",
                    Error = new ErrorDetail
                    {
                        Code = "PHASE_DEADLINE_EXCEEDED",
                        Message = $"No phase transition observed within the deadline for phase '{currentPhase}'.",
                        Details = new Dictionary<string, object?>
                        {
                            ["phase"] = currentPhase,
                            ["deadline_seconds"] = deadlineSeconds,
                        },
                    },
                },
            });

        File.WriteAllText(resultPath, timeoutResult.ToJson());
        Console.WriteLine(timeoutResult.ToJson());
        return 1;
    }

    private static int HandleCleanExit(Process worker, JobManifest manifest, string resultPath)
    {
        string resultJson;
        try
        {
            resultJson = File.ReadAllText(resultPath);
        }
        catch (Exception ex)
        {
            return WorkerExitedWithoutResult(worker, manifest, resultPath, $"the result file could not be read: {ex.Message}");
        }

        if (string.IsNullOrWhiteSpace(resultJson))
        {
            // resultPath was truncated to empty before the worker was
            // launched (see Main). An empty file here means the worker
            // process exited without ever reaching its own
            // File.WriteAllText(resultPath, ...) call -- e.g. an unhandled
            // exception mid-job -- and there is nothing trustworthy to read.
            // Trusting whatever bytes happen to sit at this path (a stale
            // result from an earlier run reusing the same directory) is
            // exactly the "supervisor exits believing success when the
            // worker actually died" failure mode this module exists to
            // prevent.
            return WorkerExitedWithoutResult(worker, manifest, resultPath,
                "the result file was empty -- the worker exited without writing a result for this run.");
        }

        ResultDocument resultDoc;
        try
        {
            resultDoc = ResultDocument.Parse(resultJson);
        }
        catch (Exception ex)
        {
            return WorkerExitedWithoutResult(worker, manifest, resultPath,
                $"the result file did not contain a valid result document: {ex.Message}");
        }

        // A clean worker exit within all deadlines is a supervision success --
        // the worker's own final_state/ok fields (SUCCEEDED or FAILED) carry
        // the job outcome; a caller must read those, not this process's exit
        // code, to learn whether the job itself succeeded. See README.md.
        Console.WriteLine(resultDoc.ToJson());
        return 0;
    }

    /// <summary>The worker process exited (for whatever reason -- including a
    /// crash before it could write its own result.json) without leaving a
    /// trustworthy result document behind. Writes a synthetic FAILED result
    /// (ok=false) so a caller reading resultPath never sees a stale success,
    /// and returns a nonzero exit code.</summary>
    private static int WorkerExitedWithoutResult(Process worker, JobManifest manifest, string resultPath, string detail)
    {
        var message = $"Worker process exited (exit code {worker.ExitCode}) but {detail} " +
                      "Treating this run as failed rather than trusting a stale or missing result file.";
        Console.Error.WriteLine(message);

        var crashResult = ResultDocument.Build(
            runId: $"supervisor-worker-exited-without-result-{Guid.NewGuid():N}",
            idempotencyKey: manifest.IdempotencyKey,
            finalState: "FAILED",
            steps: new List<StepResult>
            {
                new()
                {
                    StepIndex = -1,
                    Type = "supervisor",
                    Status = "failed",
                    Message = message,
                    Error = new ErrorDetail
                    {
                        Code = "WORKER_EXITED_WITHOUT_RESULT",
                        Message = detail,
                        Details = new Dictionary<string, object?> { ["worker_exit_code"] = worker.ExitCode },
                    },
                },
            });

        File.WriteAllText(resultPath, crashResult.ToJson());
        Console.WriteLine(crashResult.ToJson());
        return 1;
    }

    private static void EnsureParentDirectory(string path)
    {
        var directory = Path.GetDirectoryName(Path.GetFullPath(path));
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }
    }
}
