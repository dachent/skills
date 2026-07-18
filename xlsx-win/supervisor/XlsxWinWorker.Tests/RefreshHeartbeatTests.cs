using XlsxWinContracts;
using XlsxWinWorker;

namespace XlsxWinWorker.Tests;

/// <summary>
/// Proves StepRunner.RefreshOneConnection's heartbeat emission deterministically,
/// against a plain fake `dynamic` connection object -- no real Excel/COM
/// involved, and no dependency on how long a real connection actually takes to
/// refresh (see supervisor/README.md's "Heartbeat" notes: real Power-Query/
/// Mashup OLEDB connections in this codebase's own certification fixtures were
/// confirmed, via direct COM probing, to refresh fully synchronously inside
/// the Refresh() call itself, leaving this polling loop no real time to run --
/// a real end-to-end proof of "heartbeat fires during a long real refresh"
/// is therefore not obtainable with those fixtures. This test instead proves
/// the mechanism itself is correct: given a connection that keeps reporting
/// `Refreshing = true` for longer than the configured heartbeat interval (a
/// real, if less common, provider behavior this loop exists to handle), at
/// least one heartbeat event is emitted before completion.
///
/// `dynamic` binds by runtime member lookup, not COM identity -- passing a
/// plain C# object with matching member names/shapes (`Name`, `Refresh()`,
/// `OLEDBConnection.BackgroundQuery`/`.Refreshing`) exercises exactly the
/// same code paths (TrySetBackgroundQueryOff, IsStillRefreshing, the
/// heartbeat loop itself) that a real COM connection object would.
/// </summary>
public class RefreshHeartbeatTests
{
    // Must be public (not private/internal): RefreshOneConnection's dynamic
    // dispatch runs from XlsxWinWorker.dll's own call site, which has no
    // visibility into a private or internal type defined in this separate
    // test assembly -- the DLR's runtime binder enforces normal C#
    // accessibility rules across assembly boundaries, so a private nested
    // class here would silently fail to bind (`'object' does not contain a
    // definition for ...`) despite genuinely having that member.
    public sealed class FakeOledbConnection
    {
        private int _remainingRefreshingReports;

        public FakeOledbConnection(int remainingRefreshingReports) =>
            _remainingRefreshingReports = remainingRefreshingReports;

        public bool BackgroundQuery { get; set; }

        // Reports "still refreshing" for a fixed number of checks, then
        // false -- simulating a connection whose Refresh() call returns
        // quickly but whose actual data fetch keeps running in the
        // background for a while afterward.
        public bool Refreshing
        {
            get
            {
                if (_remainingRefreshingReports <= 0)
                {
                    return false;
                }

                _remainingRefreshingReports--;
                return true;
            }
        }
    }

    // Public for the same cross-assembly dynamic-dispatch reason as
    // FakeOledbConnection above.
    public sealed class FakeConnection
    {
        public FakeConnection(int remainingRefreshingReports)
        {
            OLEDBConnection = new FakeOledbConnection(remainingRefreshingReports);
        }

        public string Name => "FakeConnection";

        public FakeOledbConnection OLEDBConnection { get; }

        // Simulates a genuinely asynchronous refresh: the call itself
        // returns immediately, and OLEDBConnection.Refreshing is what
        // actually reports completion (via IsStillRefreshing's polling).
        public void Refresh()
        {
        }
    }

    [Fact]
    public void RefreshOneConnection_emits_at_least_one_heartbeat_when_still_refreshing_past_the_interval()
    {
        var eventsPath = Path.Combine(Path.GetTempPath(), $"xlsxwin-heartbeat-test-{Guid.NewGuid():N}.jsonl");
        try
        {
            using (var events = new EventWriter(eventsPath))
            {
                // Small interval + several PumpingDelay(200ms) ticks --
                // deterministic and fast (well under a second), unlike
                // production's real 5-second default.
                var runner = new StepRunner(
                    new ExcelSession(),
                    events,
                    runId: "heartbeat-test",
                    timeouts: new JobTimeouts(),
                    heartbeatInterval: TimeSpan.FromMilliseconds(50));

                dynamic fakeConnection = new FakeConnection(remainingRefreshingReports: 4);
                var deadline = DateTime.UtcNow.AddSeconds(30);

                runner.RefreshOneConnection(fakeConnection, deadline);
            }

            var heartbeatLines = File.ReadAllLines(eventsPath)
                .Select(line => WorkerEvent.TryParse(line))
                .Where(evt => evt is not null)
                .Select(evt => evt!)
                .Where(evt => evt.Phase == "REFRESHING_CONNECTIONS" && evt.Message == "heartbeat: still refreshing.")
                .ToList();

            Assert.NotEmpty(heartbeatLines);
        }
        finally
        {
            File.Delete(eventsPath);
        }
    }

    [Fact]
    public void RefreshOneConnection_emits_no_heartbeat_for_a_connection_that_finishes_immediately()
    {
        // The common, confirmed-real case (see class doc): a connection
        // whose Refresh() call itself is synchronous never reports
        // Refreshing = true afterward, so the loop returns immediately and
        // no heartbeat fires -- correctly, since there is nothing left to
        // report on.
        var eventsPath = Path.Combine(Path.GetTempPath(), $"xlsxwin-heartbeat-test-{Guid.NewGuid():N}.jsonl");
        try
        {
            using (var events = new EventWriter(eventsPath))
            {
                var runner = new StepRunner(
                    new ExcelSession(),
                    events,
                    runId: "heartbeat-test-none",
                    timeouts: new JobTimeouts(),
                    heartbeatInterval: TimeSpan.FromMilliseconds(50));

                dynamic fakeConnection = new FakeConnection(remainingRefreshingReports: 0);
                var deadline = DateTime.UtcNow.AddSeconds(30);

                runner.RefreshOneConnection(fakeConnection, deadline);
            }

            var heartbeatLines = File.ReadAllLines(eventsPath)
                .Select(line => WorkerEvent.TryParse(line))
                .Where(evt => evt is not null && evt!.Message == "heartbeat: still refreshing.")
                .ToList();

            Assert.Empty(heartbeatLines);
        }
        finally
        {
            File.Delete(eventsPath);
        }
    }
}
