using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

public sealed class JobManifest
{
    [JsonPropertyName("schema_version")]
    public string SchemaVersion { get; set; } = "2.0";

    [JsonPropertyName("idempotency_key")]
    public string IdempotencyKey { get; set; } = "";

    [JsonPropertyName("steps")]
    public List<JobStep> Steps { get; set; } = new();

    [JsonPropertyName("timeouts")]
    public JobTimeouts? Timeouts { get; set; }

    public static JobManifest Parse(string json) =>
        JsonSerializer.Deserialize<JobManifest>(json, JsonDefaults.Options)
        ?? throw new InvalidOperationException("Job manifest deserialized to null.");

    public string ToJson() => JsonSerializer.Serialize(this, JsonDefaults.Options);
}

public sealed class JobTimeouts
{
    // v2.0 compatibility fields.
    [JsonPropertyName("start_excel_seconds")]
    public int StartExcelSeconds { get; set; } = 30;

    [JsonPropertyName("open_workbook_seconds")]
    public int OpenWorkbookSeconds { get; set; } = 90;

    [JsonPropertyName("refresh_total_seconds")]
    public int RefreshTotalSeconds { get; set; } = 1800;

    [JsonPropertyName("calculation_seconds")]
    public int CalculationSeconds { get; set; } = 900;

    [JsonPropertyName("save_seconds")]
    public int SaveSeconds { get; set; } = 90;

    [JsonPropertyName("close_seconds")]
    public int CloseSeconds { get; set; } = 30;

    // v2.1 absolute phase, whole-job, inactivity, and shutdown deadlines.
    [JsonPropertyName("preflight_seconds")]
    public int PreflightSeconds { get; set; } = 120;

    [JsonPropertyName("write_seconds")]
    public int WriteSeconds { get; set; } = 1800;

    [JsonPropertyName("pivot_seconds")]
    public int PivotSeconds { get; set; } = 600;

    [JsonPropertyName("reopen_seconds")]
    public int ReopenSeconds { get; set; } = 600;

    [JsonPropertyName("validation_seconds")]
    public int ValidationSeconds { get; set; } = 600;

    [JsonPropertyName("whole_job_seconds")]
    public int WholeJobSeconds { get; set; } = 3600;

    [JsonPropertyName("inactivity_seconds")]
    public int InactivitySeconds { get; set; } = 300;

    [JsonPropertyName("shutdown_seconds")]
    public int ShutdownSeconds { get; set; } = 30;

    public int? ForPhase(string phase) => phase switch
    {
        "STARTING_EXCEL" => StartExcelSeconds,
        "OPENING_WORKBOOK" => OpenWorkbookSeconds,
        "COMPOSITE_PREFLIGHT" => PreflightSeconds,
        "APPLYING_EDITS" => WriteSeconds,
        "REFRESHING_CONNECTIONS" => RefreshTotalSeconds,
        "REFRESHING_DATA_MODEL" => RefreshTotalSeconds,
        "REFRESHING_PIVOTS" => PivotSeconds > 0 ? PivotSeconds : RefreshTotalSeconds,
        "CALCULATING" => CalculationSeconds,
        "SAVING" => SaveSeconds,
        "REOPENING" => ReopenSeconds,
        "VALIDATING" => ValidationSeconds,
        "SUCCEEDED" => CloseSeconds,
        "FAILED" => CloseSeconds,
        _ => null,
    };
}

[JsonPolymorphic(TypeDiscriminatorPropertyName = "type", UnknownDerivedTypeHandling = JsonUnknownDerivedTypeHandling.FailSerialization)]
[JsonDerivedType(typeof(OpenStep), "open")]
[JsonDerivedType(typeof(RefreshStep), "refresh")]
[JsonDerivedType(typeof(RecalcStep), "recalc")]
[JsonDerivedType(typeof(RunApprovedMacroStep), "run_approved_macro")]
[JsonDerivedType(typeof(SaveAsStep), "save_as")]
[JsonDerivedType(typeof(AppendTableRowsStep), "append_table_rows")]
[JsonDerivedType(typeof(ReplaceTableDataStep), "replace_table_data")]
public abstract class JobStep;

public sealed class OpenStep : JobStep
{
    [JsonPropertyName("workbook_path")]
    public string WorkbookPath { get; set; } = "";

    [JsonPropertyName("read_only")]
    public bool? ReadOnly { get; set; }

    [JsonPropertyName("update_links")]
    public bool? UpdateLinks { get; set; }
}

public sealed class RefreshStep : JobStep
{
    [JsonPropertyName("connections")]
    [JsonConverter(typeof(ConnectionsSpecConverter))]
    public ConnectionsSpec Connections { get; set; } = ConnectionsSpec.AllConnections;
}

public sealed class ConnectionsSpec
{
    public bool All { get; init; }
    public IReadOnlyList<string> Names { get; init; } = Array.Empty<string>();
    public static readonly ConnectionsSpec AllConnections = new() { All = true };
    public static ConnectionsSpec Explicit(IReadOnlyList<string> names) => new() { All = false, Names = names };
}

public sealed class ConnectionsSpecConverter : JsonConverter<ConnectionsSpec>
{
    public override ConnectionsSpec Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            var value = reader.GetString();
            if (value != "all") throw new JsonException($"Unexpected 'connections' string value: '{value}'. Only \"all\" is valid.");
            return ConnectionsSpec.AllConnections;
        }
        if (reader.TokenType == JsonTokenType.StartArray)
        {
            var names = new List<string>();
            while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
            {
                if (reader.TokenType != JsonTokenType.String) throw new JsonException("Expected an array of connection name strings.");
                names.Add(reader.GetString()!);
            }
            return ConnectionsSpec.Explicit(names);
        }
        throw new JsonException("Expected 'connections' to be \"all\" or an array of strings.");
    }

    public override void Write(Utf8JsonWriter writer, ConnectionsSpec value, JsonSerializerOptions options)
    {
        if (value.All)
        {
            writer.WriteStringValue("all");
            return;
        }
        writer.WriteStartArray();
        foreach (var name in value.Names) writer.WriteStringValue(name);
        writer.WriteEndArray();
    }
}

public sealed class RecalcStep : JobStep
{
    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "full_rebuild";

    [JsonPropertyName("timeout_seconds")]
    public int? TimeoutSeconds { get; set; }
}

public sealed class RunApprovedMacroStep : JobStep
{
    [JsonPropertyName("macro_name")]
    public string MacroName { get; set; } = "";
}

public sealed class SaveAsStep : JobStep
{
    [JsonPropertyName("output_path")]
    public string OutputPath { get; set; } = "";

    [JsonPropertyName("overwrite")]
    public bool? Overwrite { get; set; }
}

public abstract class CompositeTableStep : JobStep
{
    [JsonPropertyName("operation_version")]
    public string OperationVersion { get; set; } = "1.0";

    [JsonPropertyName("workbook_path")]
    public string WorkbookPath { get; set; } = "";

    [JsonPropertyName("workbook_sha256")]
    public string WorkbookSha256 { get; set; } = "";

    [JsonPropertyName("output_path")]
    public string OutputPath { get; set; } = "";

    [JsonPropertyName("table")]
    public CompositeTableSpec Table { get; set; } = new();

    [JsonPropertyName("source")]
    public CompositeSourceSpec Source { get; set; } = new();

    [JsonPropertyName("dependent_pivots")]
    public CompositePivotSpec DependentPivots { get; set; } = new();

    [JsonPropertyName("capability_profile")]
    public string CapabilityProfile { get; set; } = "";

    [JsonIgnore]
    public abstract string OperationType { get; }
}

public sealed class AppendTableRowsStep : CompositeTableStep
{
    public override string OperationType => "append_table_rows";
}

public sealed class ReplaceTableDataStep : CompositeTableStep
{
    public override string OperationType => "replace_table_data";
}

public sealed class CompositeTableSpec
{
    [JsonPropertyName("sheet")]
    public string Sheet { get; set; } = "";
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("existing_body_rows")]
    public int ExistingBodyRows { get; set; }
    [JsonPropertyName("final_body_rows")]
    public int FinalBodyRows { get; set; }
    [JsonPropertyName("column_count")]
    public int ColumnCount { get; set; }
    [JsonPropertyName("writable_runs")]
    public int WritableRuns { get; set; }
    [JsonPropertyName("columns")]
    public List<CompositeColumnSpec> Columns { get; set; } = new();
    [JsonPropertyName("filters")]
    public string Filters { get; set; } = "none";
    [JsonPropertyName("totals")]
    public bool Totals { get; set; }
    [JsonPropertyName("saved_sort")]
    public SavedSortSpec? SavedSort { get; set; }
}

public sealed class CompositeColumnSpec
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";
    [JsonPropertyName("role")]
    public string Role { get; set; } = "";
    [JsonPropertyName("logical_type")]
    public string LogicalType { get; set; } = "";
    [JsonPropertyName("number_format")]
    public string? NumberFormat { get; set; }
}

public sealed class SavedSortSpec
{
    [JsonPropertyName("column")]
    public string Column { get; set; } = "";
    [JsonPropertyName("direction")]
    public string Direction { get; set; } = "";
    [JsonPropertyName("behavior")]
    public string Behavior { get; set; } = "";
}

public sealed class CompositeSourceSpec
{
    [JsonPropertyName("path")]
    public string Path { get; set; } = "";
    [JsonPropertyName("raw_sha256")]
    public string RawSha256 { get; set; } = "";
    [JsonPropertyName("schema_path")]
    public string SchemaPath { get; set; } = "";
    [JsonPropertyName("schema_sha256")]
    public string SchemaSha256 { get; set; } = "";
    [JsonPropertyName("canonical_sha256")]
    public string CanonicalSha256 { get; set; } = "";
    [JsonPropertyName("row_count")]
    public int RowCount { get; set; }
    [JsonPropertyName("column_count")]
    public int ColumnCount { get; set; }
    [JsonPropertyName("encoded_bytes")]
    public long EncodedBytes { get; set; }
    [JsonPropertyName("text_bytes")]
    public long TextBytes { get; set; }
    [JsonPropertyName("cardinality")]
    public List<int> Cardinality { get; set; } = new();
    [JsonPropertyName("writable_runs")]
    public int WritableRuns { get; set; }
}

public sealed class CompositePivotSpec
{
    [JsonPropertyName("mode")]
    public string Mode { get; set; } = "";
    [JsonPropertyName("profile")]
    public string Profile { get; set; } = "";
    [JsonPropertyName("cache_count")]
    public int CacheCount { get; set; }
    [JsonPropertyName("report_count")]
    public int ReportCount { get; set; }
    [JsonPropertyName("oracle_path")]
    public string OraclePath { get; set; } = "";
    [JsonPropertyName("oracle_sha256")]
    public string OracleSha256 { get; set; } = "";
}

public static class JsonDefaults
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}
