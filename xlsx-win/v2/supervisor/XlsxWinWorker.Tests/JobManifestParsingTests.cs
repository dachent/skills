using XlsxWinContracts;

namespace XlsxWinWorker.Tests;

public class JobManifestParsingTests
{
    private const string SampleManifestJson = """
    {
      "schema_version": "2.0",
      "idempotency_key": "job-123",
      "timeouts": {
        "start_excel_seconds": 30,
        "open_workbook_seconds": 90,
        "refresh_total_seconds": 1800,
        "calculation_seconds": 900,
        "save_seconds": 90,
        "close_seconds": 30
      },
      "steps": [
        { "type": "open", "workbook_path": "C:\\jobs\\input\\model.xlsx", "update_links": false },
        { "type": "refresh", "connections": "all" },
        { "type": "refresh", "connections": ["Query - Sales", "Query - Costs"] },
        { "type": "recalc", "mode": "full_rebuild" },
        { "type": "run_approved_macro", "macro_name": "RefreshDashboard" },
        { "type": "save_as", "output_path": "C:\\jobs\\output\\model.xlsx", "overwrite": true }
      ]
    }
    """;

    [Fact]
    public void Parses_all_step_types_in_order()
    {
        var manifest = JobManifest.Parse(SampleManifestJson);

        Assert.Equal("2.0", manifest.SchemaVersion);
        Assert.Equal("job-123", manifest.IdempotencyKey);
        Assert.Equal(6, manifest.Steps.Count);

        Assert.IsType<OpenStep>(manifest.Steps[0]);
        Assert.IsType<RefreshStep>(manifest.Steps[1]);
        Assert.IsType<RefreshStep>(manifest.Steps[2]);
        Assert.IsType<RecalcStep>(manifest.Steps[3]);
        Assert.IsType<RunApprovedMacroStep>(manifest.Steps[4]);
        Assert.IsType<SaveAsStep>(manifest.Steps[5]);
    }

    [Fact]
    public void Parses_open_step_fields()
    {
        var manifest = JobManifest.Parse(SampleManifestJson);
        var open = Assert.IsType<OpenStep>(manifest.Steps[0]);

        Assert.Equal("C:\\jobs\\input\\model.xlsx", open.WorkbookPath);
        Assert.False(open.UpdateLinks);
    }

    [Fact]
    public void Parses_refresh_connections_all_literal()
    {
        var manifest = JobManifest.Parse(SampleManifestJson);
        var refresh = Assert.IsType<RefreshStep>(manifest.Steps[1]);

        Assert.True(refresh.Connections.All);
        Assert.Empty(refresh.Connections.Names);
    }

    [Fact]
    public void Parses_refresh_connections_explicit_list()
    {
        var manifest = JobManifest.Parse(SampleManifestJson);
        var refresh = Assert.IsType<RefreshStep>(manifest.Steps[2]);

        Assert.False(refresh.Connections.All);
        Assert.Equal(new[] { "Query - Sales", "Query - Costs" }, refresh.Connections.Names);
    }

    [Fact]
    public void Parses_timeouts()
    {
        var manifest = JobManifest.Parse(SampleManifestJson);

        Assert.NotNull(manifest.Timeouts);
        Assert.Equal(30, manifest.Timeouts!.StartExcelSeconds);
        Assert.Equal(1800, manifest.Timeouts.RefreshTotalSeconds);
    }

    [Fact]
    public void Missing_timeouts_object_is_tolerated_and_null()
    {
        const string json = """
        {
          "schema_version": "2.0",
          "idempotency_key": "job-456",
          "steps": [ { "type": "recalc" } ]
        }
        """;

        var manifest = JobManifest.Parse(json);

        Assert.Null(manifest.Timeouts);
        var recalc = Assert.IsType<RecalcStep>(manifest.Steps[0]);
        Assert.Equal("full_rebuild", recalc.Mode); // schema-documented default
    }

    [Fact]
    public void Round_trips_through_serialize_and_reparse()
    {
        var original = JobManifest.Parse(SampleManifestJson);
        var reparsed = JobManifest.Parse(original.ToJson());

        Assert.Equal(original.IdempotencyKey, reparsed.IdempotencyKey);
        Assert.Equal(original.Steps.Count, reparsed.Steps.Count);
        Assert.Equal(
            ((SaveAsStep)original.Steps[^1]).OutputPath,
            ((SaveAsStep)reparsed.Steps[^1]).OutputPath);
    }

    [Fact]
    public void Unknown_step_type_throws()
    {
        const string json = """
        {
          "schema_version": "2.0",
          "idempotency_key": "job-789",
          "steps": [ { "type": "delete_everything" } ]
        }
        """;

        Assert.ThrowsAny<Exception>(() => JobManifest.Parse(json));
    }
}
