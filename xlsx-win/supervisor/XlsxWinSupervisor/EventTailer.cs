using XlsxWinContracts;

namespace XlsxWinSupervisor;

/// <summary>
/// Tails a JSONL events file the worker process is appending to concurrently.
/// Keeps a single open FileStream (opened with FileShare.ReadWrite so it does
/// not block the worker's own writer) and remembers its read position between
/// calls, so repeated calls to <see cref="ReadNewEvents"/> only return lines
/// appended since the previous call.
/// </summary>
public sealed class EventTailer : IDisposable
{
    private readonly FileStream _stream;
    private readonly StreamReader _reader;

    public EventTailer(string path)
    {
        var directory = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(directory))
        {
            Directory.CreateDirectory(directory);
        }

        _stream = new FileStream(path, FileMode.OpenOrCreate, FileAccess.Read, FileShare.ReadWrite);
        _reader = new StreamReader(_stream);
    }

    /// <summary>Count of non-blank lines that failed to parse as a
    /// WorkerEvent since this tailer was constructed. Exposed so a dropped
    /// phase-transition/excel_pid event is at least observable, rather than
    /// vanishing with zero diagnostic trail.</summary>
    public int MalformedLineCount { get; private set; }

    public List<WorkerEvent> ReadNewEvents()
    {
        var events = new List<WorkerEvent>();
        string? line;
        while ((line = _reader.ReadLine()) is not null)
        {
            var evt = WorkerEvent.TryParse(line, out var parseError);
            if (evt is not null)
            {
                events.Add(evt);
                continue;
            }

            if (string.IsNullOrWhiteSpace(line))
            {
                continue;
            }

            // A transient malformed/partial-line read is plausible here since
            // this tailer reads a file the worker is concurrently appending
            // to. The StreamReader position has already advanced past this
            // line, so without logging it, a dropped phase-transition or
            // excel_pid announcement would vanish with zero diagnostic trail.
            MalformedLineCount++;
            Console.Error.WriteLine(
                $"Warning: dropped unparseable events.jsonl line #{MalformedLineCount}: " +
                $"{parseError ?? "unknown parse error"}. Raw line: {line}");
        }

        return events;
    }

    public void Dispose()
    {
        _reader.Dispose();
    }
}
