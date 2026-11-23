using XlsxWinContracts;

namespace XlsxWinWorker.Tests;

public class WorkerHeartbeatTests
{
    [Fact]
    public void Heartbeat_fires_while_the_calling_thread_is_blocked()
    {
        var path = TempPath();
        try
        {
            using (var events = new EventWriter(path))
            {
                events.Emit(new WorkerEvent { RunId = "run", Phase = "COMPOSITE_PREFLIGHT" });
                using var heartbeat = new WorkerHeartbeat(events, "run", TimeSpan.FromMilliseconds(50));
                using var blocked = new ManualResetEventSlim(false);
                blocked.Wait(TimeSpan.FromMilliseconds(250));
            }

            Assert.Contains(ReadEvents(path), evt =>
                evt.Phase == "COMPOSITE_PREFLIGHT" && evt.Message == "heartbeat: worker still running.");
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Concurrent_heartbeats_parse_and_never_use_a_stale_phase()
    {
        var path = TempPath();
        try
        {
            using (var events = new EventWriter(path))
            {
                events.Emit(new WorkerEvent { RunId = "run", Phase = "PHASE_A" });
                using var heartbeat = new WorkerHeartbeat(events, "run", TimeSpan.FromMilliseconds(1));
                for (var index = 0; index < 200; index++)
                {
                    events.Emit(new WorkerEvent { RunId = "run", Phase = "PHASE_A" });
                    events.Emit(new WorkerEvent { RunId = "run", Phase = "PHASE_B" });
                }
            }

            var observedEvents = ReadEvents(path);
            Assert.Contains(observedEvents, evt => evt.Message == "heartbeat: worker still running.");
            var latestOrdinaryPhase = "";
            foreach (var evt in observedEvents)
            {
                if (evt.Message == "heartbeat: worker still running.")
                {
                    Assert.Equal(latestOrdinaryPhase, evt.Phase);
                }
                else
                {
                    latestOrdinaryPhase = evt.Phase;
                }
            }
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Dispose_stops_later_writes()
    {
        var path = TempPath();
        try
        {
            using var events = new EventWriter(path);
            events.Emit(new WorkerEvent { RunId = "run", Phase = "COMPOSITE_PREFLIGHT" });
            var heartbeat = new WorkerHeartbeat(events, "run", TimeSpan.FromMilliseconds(20));
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(2);
            while (!ReadEvents(path).Any(evt => evt.Message == "heartbeat: worker still running."))
            {
                Assert.True(DateTime.UtcNow < deadline, "No heartbeat arrived before the test deadline.");
                Thread.Sleep(10);
            }
            heartbeat.Dispose();
            var count = ReadEvents(path).Count;
            Thread.Sleep(100);
            Assert.Equal(count, ReadEvents(path).Count);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Writer_failure_is_exposed_to_the_heartbeat_owner()
    {
        var path = TempPath();
        try
        {
            using var events = new EventWriter(path);
            using var heartbeat = new WorkerHeartbeat(events, "run", TimeSpan.FromMilliseconds(20));
            events.Dispose();
            var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(2);
            while (heartbeat.Fault is null && DateTime.UtcNow < deadline)
            {
                Thread.Sleep(10);
            }
            Assert.NotNull(heartbeat.Fault);
        }
        finally
        {
            File.Delete(path);
        }
    }

    private static string TempPath() =>
        Path.Combine(Path.GetTempPath(), $"xlsxwin-worker-heartbeat-{Guid.NewGuid():N}.jsonl");

    private static List<WorkerEvent> ReadEvents(string path)
    {
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite);
        using var reader = new StreamReader(stream);
        return reader.ReadToEnd()
            .Split(new[] { "\r\n", "\n" }, StringSplitOptions.RemoveEmptyEntries)
            .Select(ParseEvent)
            .ToList();
    }

    private static WorkerEvent ParseEvent(string line)
    {
        var evt = WorkerEvent.TryParse(line, out var parseError);
        if (evt is null)
        {
            throw new InvalidOperationException($"Malformed worker event: {parseError}");
        }
        return evt;
    }
}
