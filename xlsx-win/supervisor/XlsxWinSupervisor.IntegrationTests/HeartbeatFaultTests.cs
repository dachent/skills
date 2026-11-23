using XlsxWinContracts;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

public class HeartbeatFaultTests
{
    public HeartbeatFaultTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Heartbeat_write_fault_fails_the_job_with_a_named_result()
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("input.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");
        FixtureWorkbookBuilder.CreateSimpleWorkbook(inputPath);
        var manifest = new JobManifest
        {
            IdempotencyKey = "heartbeat-fault-test",
            Steps = new List<JobStep> { new OpenStep { WorkbookPath = inputPath } },
        };
        File.WriteAllText(jobPath, manifest.ToJson());
        var extraEnv = new Dictionary<string, string>
        {
            ["XLSXWIN_TEST_SIMULATE_HEARTBEAT_FAULT"] = "1",
        };

        var runResult = SupervisorRunner.Run(
            jobPath, eventsPath, resultPath, TimeSpan.FromSeconds(120), extraEnv);
        try
        {
            Assert.Equal(1, runResult.ExitCode);
            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal("FAILED", resultDoc.FinalState);
            Assert.False(resultDoc.Ok);
            var failure = Assert.Single(resultDoc.Steps, step =>
                step.Error?.Code == "WORKER_HEARTBEAT_WRITE_FAILED");
            Assert.Equal("failed", failure.Status);
        }
        finally
        {
            ExcelIntegrationGate.AssertNoExcelProcessSurvives();
        }
    }
}
