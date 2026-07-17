using XlsxWinContracts;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Confirms the refresh step enumerates and refreshes a workbook's
/// connections individually rather than calling a bare RefreshAll -- proven
/// both by the step result's own message and by the REFRESHING_CONNECTIONS
/// phase event, against a workbook with one real WorkbookConnection.
/// </summary>
public class PerConnectionRefreshTests
{
    public PerConnectionRefreshTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Refresh_step_refreshes_the_single_connection_individually()
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("input.xlsx");
        var outputPath = tempDir.Combine("output.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");

        FixtureWorkbookBuilder.CreateWorkbookWithConnection(inputPath);

        var manifest = new JobManifest
        {
            IdempotencyKey = "per-connection-refresh-test",
            Timeouts = new JobTimeouts
            {
                StartExcelSeconds = 30,
                OpenWorkbookSeconds = 30,
                RefreshTotalSeconds = 60,
                CalculationSeconds = 30,
                SaveSeconds = 30,
                // Generous on purpose: real verification on this machine found
                // that after a WorkbookConnection.Refresh(), EXCEL.EXE can take
                // anywhere from a few seconds to several minutes to actually
                // exit after Quit() returns (see README.md, "Known limitation:
                // connection-refresh shutdown latency"). This is the deadline
                // the *worker* waits against (via ExcelSession.CloseAndWait)
                // before the supervisor's Job Object would step in.
                //
                // NOTE: raised from 600 to 900 during a later re-verification
                // pass, but this did NOT make the test reliably pass on this
                // machine -- four independent measurements that session (three
                // at a 600s budget, one at 900s) each exceeded their
                // configured deadline by roughly the same ~47-49s margin
                // before the supervisor's own Job-Object kill fired. That
                // pattern is consistent with this specific Power-Query-backed
                // fixture's EXCEL.EXE simply not exiting on its own on this
                // machine within any of the budgets tried, rather than the
                // deadline just being set too tight. No number tried here is
                // known to be reliably sufficient; see README.md's "Known
                // limitations" update for the full evidence and why this is
                // left as an open, pre-existing, environment-specific issue
                // rather than "fixed" by this edit.
                CloseSeconds = 900,
            },
            Steps = new List<JobStep>
            {
                new OpenStep { WorkbookPath = inputPath },
                new RefreshStep { Connections = ConnectionsSpec.AllConnections },
                new SaveAsStep { OutputPath = outputPath, Overwrite = true },
            },
        };
        File.WriteAllText(jobPath, manifest.ToJson());

        // Hard test-level ceiling, comfortably above CloseSeconds so the
        // supervisor's own deadline enforcement is what governs, not this.
        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromMinutes(17));

        try
        {
            Assert.Equal(0, runResult.ExitCode);

            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal("SUCCEEDED", resultDoc.FinalState);
            Assert.True(resultDoc.Ok, $"Expected ok=true. Steps: {string.Join(", ", resultDoc.Steps.Select(s => $"{s.Type}={s.Status}:{s.Message}"))}");

            var refreshResult = Assert.Single(resultDoc.Steps, s => s.Type == "refresh");
            Assert.Equal("succeeded", refreshResult.Status);
            Assert.Contains("individually", refreshResult.Message ?? "");
            Assert.DoesNotContain("RefreshAll", refreshResult.Message ?? "", StringComparison.OrdinalIgnoreCase);

            var events = File.ReadAllLines(eventsPath)
                .Select(WorkerEvent.TryParse)
                .Where(e => e is not null)
                .Select(e => e!)
                .ToList();
            Assert.Contains(events, e => e.Phase == "REFRESHING_CONNECTIONS");
        }
        finally
        {
            ExcelIntegrationGate.AssertNoExcelProcessSurvives();
        }
    }
}
