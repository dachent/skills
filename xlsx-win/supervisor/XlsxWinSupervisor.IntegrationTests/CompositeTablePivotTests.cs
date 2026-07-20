using System.IO.Compression;
using System.Xml.Linq;
using XlsxWinContracts;

namespace XlsxWinSupervisor.IntegrationTests;

public class CompositeTablePivotTests
{
    public CompositeTablePivotTests() => ExcelIntegrationGate.PreflightOrSkip();

    [SkippableFact]
    public void Composite_append_resizes_calculates_refreshes_saves_and_fresh_reopens()
    {
        using var tempDir = new TestTempDir();
        var inputPath = tempDir.Combine("intermediate.xlsx");
        var outputPath = tempDir.Combine("output.xlsx");
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");
        FixtureWorkbookBuilder.CreateCompositeTablePivotWorkbook(inputPath);

        var manifest = new JobManifest
        {
            SchemaVersion = "2.1",
            IdempotencyKey = "composite-table-pivot-test",
            Timeouts = new JobTimeouts
            {
                StartExcelSeconds = 30,
                OpenWorkbookSeconds = 60,
                PreflightSeconds = 60,
                WriteSeconds = 60,
                CalculationSeconds = 60,
                PivotSeconds = 60,
                SaveSeconds = 60,
                ReopenSeconds = 60,
                ValidationSeconds = 60,
                CloseSeconds = 30,
                WholeJobSeconds = 240,
                InactivitySeconds = 60,
                ShutdownSeconds = 5,
            },
            Steps = new List<JobStep>
            {
                new AppendTableRowsStep
                {
                    WorkbookPath = inputPath,
                    WorkbookSha256 = new string('0', 64),
                    OutputPath = outputPath,
                    CapabilityProfile = "integration-test",
                    Table = new CompositeTableSpec
                    {
                        Sheet = "Data",
                        Name = "Data",
                        ExistingBodyRows = 2,
                        FinalBodyRows = 3,
                        ColumnCount = 3,
                        WritableRuns = 2,
                        Filters = "none",
                        Totals = false,
                        Columns = new List<CompositeColumnSpec>
                        {
                            new() { Name = "Name", Role = "writable", LogicalType = "text" },
                            new() { Name = "Calc", Role = "calculated", LogicalType = "number" },
                            new() { Name = "Value", Role = "writable", LogicalType = "number" },
                        },
                    },
                    Source = new CompositeSourceSpec
                    {
                        Path = "immutable.csv",
                        RawSha256 = new string('1', 64),
                        SchemaPath = "immutable.schema.json",
                        SchemaSha256 = new string('2', 64),
                        CanonicalSha256 = new string('3', 64),
                        RowCount = 1,
                        ColumnCount = 3,
                        EncodedBytes = 1,
                        TextBytes = 5,
                        Cardinality = new List<int> { 1, 0, 1 },
                        WritableRuns = 2,
                    },
                    DependentPivots = new CompositePivotSpec
                    {
                        Mode = "linked_only",
                        Profile = "one-cache-one-report",
                        CacheCount = 1,
                        ReportCount = 1,
                        OraclePath = "oracle.json",
                        OracleSha256 = new string('4', 64),
                    },
                },
            },
        };
        File.WriteAllText(jobPath, manifest.ToJson());

        var run = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromMinutes(5));
        var diagnostics = $"exit={run.ExitCode}\nstdout={run.Stdout}\nstderr={run.Stderr}\nevents={File.ReadAllText(eventsPath)}";
        try
        {
            Assert.True(run.ExitCode == 0, diagnostics);
            var result = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.True(result.Ok, diagnostics);
            Assert.Equal("SUCCEEDED", result.FinalState);
            Assert.Single(result.Steps);
            Assert.Equal("succeeded", result.Steps[0].Status);
            Assert.True(File.Exists(outputPath));
            var leaseBalance = Assert.Single(result.Invariants, invariant =>
                invariant.Name == "tracked_owned_rcw_lease_balance");
            Assert.True(leaseBalance.Passed, leaseBalance.Message);
            Assert.Contains("tracked_owned_rcw_high_water=", leaseBalance.Message);

            using var package = ZipFile.OpenRead(outputPath);
            var tableEntry = package.GetEntry("xl/tables/table1.xml")
                ?? throw new InvalidOperationException("Saved package has no table1.xml.");
            using var stream = tableEntry.Open();
            var table = XDocument.Load(stream).Root
                ?? throw new InvalidOperationException("Saved Table definition is empty.");
            Assert.Equal("B3:D6", table.Attribute("ref")?.Value);
        }
        finally
        {
            try { ExcelIntegrationGate.AssertNoExcelProcessSurvives(); }
            catch (Exception ex) { throw new Exception($"{ex.Message}\n{diagnostics}", ex); }
        }
    }
}
