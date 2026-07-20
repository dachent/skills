using XlsxWinContracts;

namespace XlsxWinSupervisor.IntegrationTests;

internal static class CompositeJobFixture
{
    public static JobManifest CreateManifest(string inputPath, string outputPath, string idempotencyKey) => new()
    {
        SchemaVersion = "2.1",
        IdempotencyKey = idempotencyKey,
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
                    Sheet = "Data", Name = "Data", ExistingBodyRows = 2, FinalBodyRows = 3,
                    ColumnCount = 3, WritableRuns = 2, Filters = "none", Totals = false,
                    Columns = new List<CompositeColumnSpec>
                    {
                        new() { Name = "Name", Role = "writable", LogicalType = "text" },
                        new() { Name = "Calc", Role = "calculated", LogicalType = "number" },
                        new() { Name = "Value", Role = "writable", LogicalType = "number" },
                    },
                },
                Source = new CompositeSourceSpec
                {
                    Path = "immutable.csv", RawSha256 = new string('1', 64),
                    SchemaPath = "immutable.schema.json", SchemaSha256 = new string('2', 64),
                    CanonicalSha256 = new string('3', 64), RowCount = 1, ColumnCount = 3,
                    EncodedBytes = 1, TextBytes = 5, Cardinality = new List<int> { 1, 0, 1 }, WritableRuns = 2,
                },
                DependentPivots = new CompositePivotSpec
                {
                    Mode = "linked_only", Profile = "one-cache-one-report", CacheCount = 1, ReportCount = 1,
                    OraclePath = "oracle.json", OracleSha256 = new string('4', 64),
                },
            },
        },
    };
}
