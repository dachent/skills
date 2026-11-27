using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

/// <summary>
/// One JSONL phase, heartbeat, or progress observation in the events file,
/// using the exact state names from JobStates (ported from
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

    [JsonPropertyName("rows_done")]
    public long? RowsDone { get; set; }

    [JsonPropertyName("rows_total")]
    public long? RowsTotal { get; set; }

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
    public const string AppendEventsEnvironmentVariable = "XLSXWIN_APPEND_EVENTS";

    private readonly StreamWriter _writer;
    private readonly object _sync = new();
    private string _currentPhase = "";
    private long? _rowsDone;
    private long? _rowsTotal;

    public EventWriter(string path, bool append = false)
    {
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        _writer = new StreamWriter(new FileStream(path, append ? FileMode.Append : FileMode.Create, FileAccess.Write, FileShare.Read))
        {
            AutoFlush = true,
        };
    }

    public void Emit(WorkerEvent evt)
    {
        lock (_sync)
        {
            _writer.WriteLine(evt.ToJsonLine());
            if (!string.IsNullOrEmpty(evt.Phase))
            {
                _currentPhase = evt.Phase;
            }
            if (evt.RowsDone.HasValue)
            {
                _rowsDone = evt.RowsDone;
            }
            if (evt.RowsTotal.HasValue)
            {
                _rowsTotal = evt.RowsTotal;
            }
        }
    }

    public void EmitHeartbeat(string runId)
    {
        lock (_sync)
        {
            _writer.WriteLine(new WorkerEvent
            {
                RunId = runId,
                Phase = _currentPhase,
                Message = "heartbeat: worker still running.",
                RowsDone = _rowsDone,
                RowsTotal = _rowsTotal,
            }.ToJsonLine());
        }
    }

    public void Dispose()
    {
        lock (_sync)
        {
            _writer.Dispose();
        }
    }
}
