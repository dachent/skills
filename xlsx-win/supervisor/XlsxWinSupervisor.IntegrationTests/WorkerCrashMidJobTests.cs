using XlsxWinContracts;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Worker-crash-mid-job: the specific scenario the #36 review's blocker
/// finding was about -- a worker that dies before writing its own
/// result.json must never cause a stale/prior result to be echoed as
/// success -- was fixed and unit-tested at the Program.cs level
/// (WorkerExitedWithoutResult), but never proven through a real end-to-end
/// supervisor invocation with an actually-crashing worker process. This test
/// closes that gap: the worker (via the test-only
/// XLSXWIN_TEST_SIMULATE_CRASH_AFTER_STEP env var) throws a genuinely
/// unhandled exception after completing its first step (open) but before
/// running/writing anything further, and this test confirms the
/// supervisor's own exit code and result document correctly report a
/// failure -- never a stale or missing-result success -- and that no Excel
/// process survives.
///
/// A stale-result regression is additionally guarded against directly: this
/// test seeds resultPath with a fake prior SUCCEEDED document before
/// launching the supervisor, so if the supervisor's own truncate-before-run
/// logic (Program.cs Main) or its WorkerExitedWithoutResult fallback ever
/// regressed, this test would catch it echoing that stale document back
/// instead of writing a fresh FAILED one.
/// </summary>
public class WorkerCrashMidJobTests
{
    public WorkerCrashMidJobTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Worker_crash_after_first_step_is_reported_as_failure_not_stale_success()
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("input.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");

        FixtureWorkbookBuilder.CreateSimpleWorkbook(inputPath);

        // Seed a stale prior "success" at this exact result path, before the
        // supervisor ever runs. If the supervisor's truncate-on-start /
        // WorkerExitedWithoutResult handling regressed, this is exactly what
        // a caller would otherwise see echoed back as this run's outcome.
        var staleResult = ResultDocument.Build(
            runId: "stale-prior-run",
            idempotencyKey: "worker-crash-test",
            finalState: "SUCCEEDED",
            steps: new List<StepResult>
            {
                new() { StepIndex = 0, Type = "open", Status = "succeeded", Message = "stale" },
            });
        File.WriteAllText(resultPath, staleResult.ToJson());

        var manifest = new JobManifest
        {
            IdempotencyKey = "worker-crash-test",
            Timeouts = new JobTimeouts
            {
                StartExcelSeconds = 30,
                OpenWorkbookSeconds = 30,
                RefreshTotalSeconds = 30,
                CalculationSeconds = 30,
                SaveSeconds = 30,
                // The crash happens right after the first (open) step, well
                // before the worker would ever reach CloseAndWait's
                // indefinite wait -- this deadline exists only as a generic
                // safety net, not because the crash path is expected to be
                // slow.
                CloseSeconds = 30,
            },
            Steps = new List<JobStep>
            {
                new OpenStep { WorkbookPath = inputPath },
                // These steps are never reached: the crash fires after
                // completedStepCount == 1 (i.e. right after "open"
                // finishes), which is before the worker advances to this
                // step.
                new RecalcStep { Mode = "full_rebuild" },
            },
        };
        File.WriteAllText(jobPath, manifest.ToJson());

        var extraEnv = new Dictionary<string, string>
        {
            ["XLSXWIN_TEST_SIMULATE_CRASH_AFTER_STEP"] = "1",
        };

        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromMinutes(3), extraEnv);

        var diagnostics =
            $"exitCode={runResult.ExitCode} elapsed={runResult.Elapsed}\n" +
            $"stdout={runResult.Stdout}\nstderr={runResult.Stderr}\n" +
            $"events.jsonl=\n{(File.Exists(eventsPath) ? File.ReadAllText(eventsPath) : "<missing>")}";

        try
        {
            // The worker exits (crashes) well within every phase deadline,
            // so the supervisor takes its non-timeout path -- but finds an
            // empty result.json and returns 1 via WorkerExitedWithoutResult,
            // not the 0 a genuine clean/successful exit would return. This
            // is what was actually observed against the real built
            // executables (confirmed empirically, not assumed): exit code 0
            // is reserved for a worker that both exited without being
            // force-terminated *and* left a trustworthy result document
            // behind, per README.md's exit-code contract.
            Assert.True(1 == runResult.ExitCode, $"Expected exit code 1 (worker exited without a trustworthy result).\n{diagnostics}");

            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));

            Assert.True(
                "FAILED" == resultDoc.FinalState,
                $"Expected FAILED, not the stale SUCCEEDED seeded before this run (or any other " +
                $"value). Actual final_state={resultDoc.FinalState}.\n{diagnostics}");
            Assert.False(resultDoc.Ok, $"Expected ok=false.\n{diagnostics}");
            Assert.NotEqual("stale-prior-run", resultDoc.RunId);

            Assert.Contains(
                resultDoc.Steps,
                s => s.Error != null && s.Error.Code == "WORKER_RESULT_UNTRUSTED");
        }
        finally
        {
            // Safety rule 5: explicit, reported verification. The worker
            // crashed before ever calling ExcelSession.CloseAndWait(), so
            // the normal "wait for Excel to actually exit" guarantee does
            // not apply here -- the unhandled exception unwinds through the
            // worker's own `using var session` (a best-effort Quit(), with
            // no wait for the process to exit), and, independently and
            // regardless of whether that best-effort Quit() alone was
            // enough, the supervisor's Job Object still holds Excel's PID
            // (assigned from the STARTING_EXCEL event emitted before the
            // crash) and tears it down when the supervisor process's own
            // `using var job` handle is disposed at the end of Main. This
            // assertion is what actually proves no orphan results, not just
            // that the mechanism exists in code.
            try
            {
                ExcelIntegrationGate.AssertNoExcelProcessSurvives();
            }
            catch (Exception ex)
            {
                throw new Exception($"{ex.Message}\n{diagnostics}", ex);
            }
        }
    }
}
