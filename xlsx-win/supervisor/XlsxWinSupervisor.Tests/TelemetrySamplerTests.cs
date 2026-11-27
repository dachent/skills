using System.Text.Json;

namespace XlsxWinSupervisor.Tests;

public class TelemetrySamplerTests
{
    [Fact]
    public void Sample_emits_the_supervisor_owned_active_deadline_snapshot()
    {
        var eventsPath = Path.Combine(Path.GetTempPath(), $"xlsxwin-telemetry-{Guid.NewGuid():N}.jsonl");
        var snapshot = new DeadlineSnapshot("CALCULATING", "phase", 100, 81, 0.81, true);
        try
        {
            using (var sampler = new TelemetrySampler(eventsPath))
            {
                sampler.Sample("CALCULATING", Environment.ProcessId, null, "periodic", snapshot);
            }

            using var document = JsonDocument.Parse(File.ReadLines(eventsPath + ".telemetry.jsonl").Single());
            var root = document.RootElement;
            Assert.Equal("CALCULATING", root.GetProperty("phase").GetString());
            Assert.Equal("periodic", root.GetProperty("reason").GetString());
            var deadline = root.GetProperty("active_deadline");
            Assert.Equal("CALCULATING", deadline.GetProperty("phase").GetString());
            Assert.Equal("phase", deadline.GetProperty("kind").GetString());
            Assert.Equal(100, deadline.GetProperty("limit_seconds").GetInt32());
            Assert.Equal(81, deadline.GetProperty("elapsed_seconds").GetDouble());
            Assert.Equal(0.81, deadline.GetProperty("consumed_ratio").GetDouble(), 6);
            Assert.True(deadline.GetProperty("warning").GetBoolean());
        }
        finally
        {
            File.Delete(eventsPath);
            File.Delete(eventsPath + ".telemetry.jsonl");
        }
    }
}
