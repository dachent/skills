using XlsxWinContracts;

namespace XlsxWinContracts.Tests;

public class CompositeManifestTests
{
    [Fact]
    public void ParsesAppendCompositeAndV21Timeouts()
    {
        const string json = """
        {
          "schema_version":"2.1",
          "idempotency_key":"job",
          "steps":[{
            "type":"append_table_rows","operation_version":"1.0",
            "workbook_path":"seed.xlsx","workbook_sha256":"x","output_path":"out.xlsx",
            "table":{"sheet":"Data","name":"Data","existing_body_rows":10,"final_body_rows":12,"column_count":1,"writable_runs":1,"columns":[{"name":"A","role":"writable","logical_type":"text"}],"filters":"none","totals":false,"saved_sort":null},
            "source":{"path":"rows.csv","raw_sha256":"a","schema_path":"schema.json","schema_sha256":"b","canonical_sha256":"c","row_count":2,"column_count":1,"encoded_bytes":10,"text_bytes":2,"cardinality":[2],"writable_runs":1},
            "dependent_pivots":{"mode":"linked_only","profile":"worksheet_simple_v1","cache_count":1,"report_count":3,"oracle_path":"oracle.json","oracle_sha256":"d"},
            "capability_profile":"p"
          }],
          "timeouts":{"preflight_seconds":120,"write_seconds":1800,"calculation_seconds":600,"pivot_seconds":600,"save_seconds":600,"reopen_seconds":600,"validation_seconds":600,"close_seconds":120,"whole_job_seconds":3600,"inactivity_seconds":300,"shutdown_seconds":30}
        }
        """;

        var manifest = JobManifest.Parse(json);
        var step = Assert.IsType<AppendTableRowsStep>(Assert.Single(manifest.Steps));
        Assert.Equal("append_table_rows", step.OperationType);
        Assert.Equal(12, step.Table.FinalBodyRows);
        Assert.Equal(1800, manifest.Timeouts!.WriteSeconds);
        Assert.Equal(600, manifest.Timeouts.ForPhase("REFRESHING_PIVOTS"));
    }
}
