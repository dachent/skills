using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

/// <summary>
/// C# model of the job manifest consumed by XlsxWinWorker / XlsxWinSupervisor.
///
/// Shape follows xlsx-win/schemas/job.schema.json from issue #34 for
/// schema_version, idempotency_key, and steps. It additionally accepts an
/// optional top-level "timeouts" object (field names reused verbatim from
/// RFC 0001's example manifest) that #34's merged schema does not yet define
/// -- see supervisor/README.md "Known gap vs job.schema.json" for why. This
/// C# model does not re-validate the document against the JSON Schema itself
/// (that remains the Python control plane's job in #34); it only needs to
/// parse the fields this increment consumes, and silently ignores unknown
/// properties, which is why the extra "timeouts" property round-trips fine
/// even though it is not yet declared in the schema file.
/// </summary>
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

/// <summary>
/// Phase deadlines. Field names are reused verbatim from RFC 0001's example
/// manifest's "timeouts" object.
/// </summary>
public sealed class JobTimeouts
{
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

    /// <summary>Deadline, in seconds, for the given state-machine phase name.
    /// Returns null for phases this increment does not enforce a deadline for
    /// (the supervisor then falls back to a generous default -- see
    /// DeadlineTracker).</summary>
    public int? ForPhase(string phase) => phase switch
    {
        "STARTING_EXCEL" => StartExcelSeconds,
        "OPENING_WORKBOOK" => OpenWorkbookSeconds,
        "REFRESHING_CONNECTIONS" => RefreshTotalSeconds,
        "REFRESHING_DATA_MODEL" => RefreshTotalSeconds,
        "REFRESHING_PIVOTS" => RefreshTotalSeconds,
        "CALCULATING" => CalculationSeconds,
        "SAVING" => SaveSeconds,
        // The worker reports SUCCEEDED/FAILED as soon as all steps have run,
        // then blocks closing/quitting Excel and waiting for the Excel
        // process to actually exit before its own process exits (see
        // ExcelSession.CloseAndWait). That wait is bounded by close_seconds,
        // not the generic default -- Quit() can return long before EXCEL.EXE
        // itself has actually finished tearing down.
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
public abstract class JobStep
{
}

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

/// <summary>Either the literal string "all", or an explicit list of connection names.</summary>
public sealed class ConnectionsSpec
{
    public bool All { get; init; }
    public IReadOnlyList<string> Names { get; init; } = Array.Empty<string>();

    public static readonly ConnectionsSpec AllConnections = new() { All = true };

    public static ConnectionsSpec Explicit(IReadOnlyList<string> names) =>
        new() { All = false, Names = names };
}

public sealed class ConnectionsSpecConverter : JsonConverter<ConnectionsSpec>
{
    public override ConnectionsSpec Read(ref Utf8JsonReader reader, Type typeToConvert, JsonSerializerOptions options)
    {
        if (reader.TokenType == JsonTokenType.String)
        {
            var value = reader.GetString();
            if (value != "all")
            {
                throw new JsonException($"Unexpected 'connections' string value: '{value}'. Only \"all\" is valid.");
            }

            return ConnectionsSpec.AllConnections;
        }

        if (reader.TokenType == JsonTokenType.StartArray)
        {
            var names = new List<string>();
            while (reader.Read() && reader.TokenType != JsonTokenType.EndArray)
            {
                if (reader.TokenType != JsonTokenType.String)
                {
                    throw new JsonException("Expected an array of connection name strings.");
                }

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
        foreach (var name in value.Names)
        {
            writer.WriteStringValue(name);
        }

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

public static class JsonDefaults
{
    public static readonly JsonSerializerOptions Options = new()
    {
        WriteIndented = false,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
    };
}
