using XlsxWinContracts;
using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class EventTailerTests : IDisposable
{
    private readonly string _tempDir;

    public EventTailerTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), "xlsxwin-tailer-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempDir);
    }

    public void Dispose()
    {
        try
        {
            Directory.Delete(_tempDir, recursive: true);
        }
        catch
        {
            // best-effort cleanup
        }
    }

    [Fact]
    public void Reads_lines_appended_after_construction()
    {
        var path = Path.Combine(_tempDir, "events.jsonl");
        File.WriteAllText(path, "");

        using var tailer = new EventTailer(path);

        Assert.Empty(tailer.ReadNewEvents());

        AppendEvent(path, new WorkerEvent { RunId = "r1", Phase = "STARTING_EXCEL" });

        var firstBatch = tailer.ReadNewEvents();
        Assert.Single(firstBatch);
        Assert.Equal("STARTING_EXCEL", firstBatch[0].Phase);

        // No new lines yet -- second call returns nothing.
        Assert.Empty(tailer.ReadNewEvents());

        AppendEvent(path, new WorkerEvent { RunId = "r1", Phase = "OPENING_WORKBOOK" });
        AppendEvent(path, new WorkerEvent { RunId = "r1", Phase = "CALCULATING", ExcelPid = 999 });

        var secondBatch = tailer.ReadNewEvents();
        Assert.Equal(2, secondBatch.Count);
        Assert.Equal("OPENING_WORKBOOK", secondBatch[0].Phase);
        Assert.Equal("CALCULATING", secondBatch[1].Phase);
        Assert.Equal(999, secondBatch[1].ExcelPid);
    }

    [Fact]
    public void Ignores_unparseable_lines_but_counts_them_as_observable_diagnostics()
    {
        var path = Path.Combine(_tempDir, "events.jsonl");
        File.WriteAllText(path, "not json at all\n");

        using var tailer = new EventTailer(path);
        Assert.Empty(tailer.ReadNewEvents());

        // A dropped phase-transition/excel_pid line must be observable, not
        // silently vanish -- see WorkerEvent.TryParse / EventTailer.ReadNewEvents.
        Assert.Equal(1, tailer.MalformedLineCount);
    }

    [Fact]
    public void Blank_lines_are_skipped_without_counting_as_malformed()
    {
        var path = Path.Combine(_tempDir, "events.jsonl");
        File.WriteAllText(path, "\n\n");

        using var tailer = new EventTailer(path);
        Assert.Empty(tailer.ReadNewEvents());
        Assert.Equal(0, tailer.MalformedLineCount);
    }

    [Fact]
    public void Creates_the_file_if_it_does_not_exist_yet()
    {
        var path = Path.Combine(_tempDir, "nested", "events.jsonl");

        using var tailer = new EventTailer(path);

        Assert.True(File.Exists(path));
        Assert.Empty(tailer.ReadNewEvents());
    }

    private static void AppendEvent(string path, WorkerEvent evt)
    {
        using var writer = new StreamWriter(new FileStream(path, FileMode.Append, FileAccess.Write, FileShare.ReadWrite));
        writer.WriteLine(evt.ToJsonLine());
    }
}
