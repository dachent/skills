using XlsxWinContracts;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Timeout/kill path: the worker is made to hang deterministically (test-only
/// XLSXWIN_TEST_SIMULATE_HANG_SECONDS), proving the supervisor's Job Object
/// actually terminates a genuinely unresponsive worker+Excel pair within a
/// bounded time -- not a cooperative shutdown.
/// </summary>
public class TimeoutKillTests
{
    public TimeoutKillTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableTheory]
    [InlineData(20, 60, "phase 'STARTING_EXCEL' deadline 20s exceeded")]
    [InlineData(60, 20, "whole-job deadline 20s exceeded")]
    public void Hanging_worker_is_force_terminated_within_bounded_time_and_leaves_no_excel_process(
        int phaseCapSeconds, int wholeJobSeconds, string expectedReason)
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("input.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");

        FixtureWorkbookBuilder.CreateSimpleWorkbook(inputPath);

        // The phase cap must comfortably exceed realistic Excel COM activation:
        // the test-only hang begins only after the exact Excel PID is contained.
        // Inactivity is shorter than the hang but longer than the five-second
        // heartbeat, so only worker activity can defer the inactivity watchdog.
        const int hangSeconds = 90; // comfortably longer than either absolute cap

        var manifest = new JobManifest
        {
            IdempotencyKey = "timeout-kill-test",
            Timeouts = new JobTimeouts
            {
                StartExcelSeconds = phaseCapSeconds,
                WholeJobSeconds = wholeJobSeconds,
                InactivitySeconds = 12,
                OpenWorkbookSeconds = 30,
                RefreshTotalSeconds = 30,
                CalculationSeconds = 30,
                SaveSeconds = 30,
                CloseSeconds = 30,
            },
            Steps = new List<JobStep> { new OpenStep { WorkbookPath = inputPath } },
        };
        File.WriteAllText(jobPath, manifest.ToJson());

        var extraEnv = new Dictionary<string, string>
        {
            ["XLSXWIN_TEST_SIMULATE_HANG_SECONDS"] = hangSeconds.ToString(),
        };

        // Hard test-level ceiling: must be well under hangSeconds, proving
        // the supervisor -- not the worker eventually waking up -- is what
        // ended the job.
        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromSeconds(150), extraEnv);

        try
        {
            Assert.True(
                runResult.Elapsed < TimeSpan.FromSeconds(hangSeconds),
                $"Supervisor took {runResult.Elapsed}, which is not meaningfully less than the " +
                $"{hangSeconds}s simulated hang -- the Job Object kill does not appear to have fired.");

            Assert.Equal(1, runResult.ExitCode);

            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal("TIMED_OUT", resultDoc.FinalState);
            Assert.False(resultDoc.Ok);
            var failure = Assert.Single(resultDoc.Steps, step => step.Status == "failed");
            Assert.Equal("ABSOLUTE_DEADLINE_EXCEEDED", failure.Error?.Code);
            Assert.Contains(expectedReason, failure.Message);

            var events = File.ReadLines(eventsPath)
                .Select(WorkerEvent.TryParse)
                .Where(evt => evt is not null)
                .Select(evt => evt!)
                .ToList();
            Assert.Contains(events, evt =>
                evt.Phase == "STARTING_EXCEL" && evt.Message == "heartbeat: worker still running.");
        }
        finally
        {
            // Safety rule 5, forced-termination variant: confirm the Job
            // Object actually killed Excel too, not just the worker.
            ExcelIntegrationGate.AssertNoExcelProcessSurvives();
        }
    }
}
