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
                // FIXED (was 900s, previously an open, pre-existing,
                // environment-specific issue that no timeout number tried
                // reliably cleared -- see git history on this file and
                // certification/README.md's "power_query_minimal" section for
                // the full before/after). Root cause: StepRunner.cs's
                // RunRefresh obtained Workbook.Connections, each Connection,
                // and each OLEDBConnection/ODBCConnection via COM property
                // access and never released any of them -- classic
                // unreleased-RCW behavior that keeps EXCEL.EXE alive past
                // Application.Quit() regardless of how long you wait. Fixed
                // by explicit Marshal.ReleaseComObject on every one of those
                // objects. Reverified after the fix: this test's own workbook
                // (a plain WorkbookConnection, not genuine Power Query M)
                // now completes and exits well within a generous 120s, so
                // this deadline is a real bound again, not a number chosen to
                // outlast an unresolved hang.
                CloseSeconds = 120,
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
        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromMinutes(5));

        try
        {
            Assert.Equal(0, runResult.ExitCode);

            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal("SUCCEEDED", resultDoc.FinalState);
            Assert.True(resultDoc.Ok, $"Expected ok=true. Steps: {string.Join(", ", resultDoc.Steps.Select(s => $"{s.Type}={s.Status}:{s.Message}"))}");

            var refreshResult = Assert.Single(resultDoc.Steps, s => s.Type == "refresh");
            Assert.Equal("succeeded", refreshResult.Status);
            // Proves the positive (refreshed individually), not a negative
            // substring-absence check: the success message legitimately says
            // "...individually (no RefreshAll)." -- a DoesNotContain("RefreshAll")
            // check here would fail on that literal phrasing despite it being
            // exactly the correct, intended message. This assertion never ran
            // to completion before the connection-refresh shutdown-latency fix
            // (see supervisor/README.md, certification/README.md): this test
            // always timed out first, so the now-fixed message was never
            // actually reached until real EXCEL.EXE process-exit stopped
            // outlasting the deadline.
            Assert.Contains("individually", refreshResult.Message ?? "");

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
