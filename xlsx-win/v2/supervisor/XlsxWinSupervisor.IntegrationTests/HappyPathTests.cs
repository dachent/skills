using XlsxWinContracts;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Happy path: a small throwaway workbook gets opened, recalculated, and
/// saved to a new path, all within one supervised worker lifecycle, and no
/// Excel process survives afterward.
/// </summary>
public class HappyPathTests
{
    public HappyPathTests()
    {
        // Safety rule 1: refuse to run if Excel is already running, checked
        // fresh in this constructor (xUnit's per-test setup), not just once.
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Open_recalc_saveas_succeeds_and_leaves_no_excel_process()
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("input.xlsx");
        var outputPath = tempDir.Combine("output.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");

        FixtureWorkbookBuilder.CreateSimpleWorkbook(inputPath);

        var manifest = new JobManifest
        {
            IdempotencyKey = "happy-path-test",
            Timeouts = new JobTimeouts
            {
                StartExcelSeconds = 30,
                OpenWorkbookSeconds = 30,
                RefreshTotalSeconds = 30,
                CalculationSeconds = 30,
                SaveSeconds = 30,
                CloseSeconds = 30,
            },
            Steps = new List<JobStep>
            {
                new OpenStep { WorkbookPath = inputPath },
                new RecalcStep { Mode = "full_rebuild" },
                new SaveAsStep { OutputPath = outputPath, Overwrite = true },
            },
        };
        File.WriteAllText(jobPath, manifest.ToJson());

        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromMinutes(3));

        var diagnostics =
            $"exitCode={runResult.ExitCode} elapsed={runResult.Elapsed}\n" +
            $"stdout={runResult.Stdout}\nstderr={runResult.Stderr}\n" +
            $"events.jsonl=\n{(File.Exists(eventsPath) ? File.ReadAllText(eventsPath) : "<missing>")}";

        try
        {
            Assert.True(0 == runResult.ExitCode, $"Expected exit code 0.\n{diagnostics}");

            var resultDoc = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.True("SUCCEEDED" == resultDoc.FinalState, $"Expected SUCCEEDED.\n{diagnostics}");
            Assert.True(resultDoc.Ok, $"Expected ok=true.\n{diagnostics}");
            Assert.All(resultDoc.Steps, s => Assert.True("succeeded" == s.Status, $"Step {s.Type} was {s.Status}: {s.Message}\n{diagnostics}"));

            Assert.True(File.Exists(outputPath), $"save_as should have produced the output workbook.\n{diagnostics}");
        }
        finally
        {
            // Safety rule 5: explicit, reported verification -- not assumed.
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
