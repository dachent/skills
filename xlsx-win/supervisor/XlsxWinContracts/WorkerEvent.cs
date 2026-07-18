using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

/// <summary>
/// One JSONL line emitted by XlsxWinWorker to its events file: one phase/state
/// transition, using the exact state names from JobStates (ported from
/// control_plane/state_machine.py).
/// </summary>
public sealed class WorkerEvent
{
    [JsonPropertyName("run_id")]
    public string RunId { get; set; } = "";

    [JsonPropertyName("timestamp")]
    public DateTimeOffset Timestamp { get; set; } = DateTimeOffset.UtcNow;

    [JsonPropertyName("phase")]
    public string Phase { get; set; } = "";

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    /// <summary>Present once the worker has captured the Excel process's own PID
    /// (via the Application object's Hwnd). The supervisor watches for this field
    /// so it can assign that PID to the same Job Object it already assigned the
    /// worker process to -- see RFC 0002 decision 8 and README "Job Object
    /// membership".</summary>
    [JsonPropertyName("excel_pid")]
    public int? ExcelPid { get; set; }

    public string ToJsonLine() => JsonSerializer.Serialize(this, JsonDefaults.Options);

    public static WorkerEvent? TryParse(string jsonLine) => TryParse(jsonLine, out _);

    /// <summary>Same as <see cref="TryParse(string)"/>, but also reports why
    /// parsing failed (null on success, or when the line was blank) so a
    /// caller tailing a concurrently-written file can log a dropped line
    /// instead of silently discarding it.</summary>
    public static WorkerEvent? TryParse(string jsonLine, out string? parseError)
    {
        parseError = null;

        if (string.IsNullOrWhiteSpace(jsonLine))
        {
            return null;
        }

        try
        {
            return JsonSerializer.Deserialize<WorkerEvent>(jsonLine, JsonDefaults.Options);
        }
        catch (JsonException ex)
        {
            parseError = ex.Message;
            return null;
        }
    }
}

/// <summary>Appends WorkerEvent lines to a file, flushing after every write so a
/// concurrently-tailing supervisor process always sees the latest line.</summary>
public sealed class EventWriter : IDisposable
{
    private readonly StreamWriter _writer;

    public EventWriter(string path)
    {
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        _writer = new StreamWriter(new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read))
        {
            AutoFlush = true,
        };
    }

    public void Emit(WorkerEvent evt)
    {
        _writer.WriteLine(evt.ToJsonLine());
    }

    public void Dispose() => _writer.Dispose();
}
