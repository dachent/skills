using XlsxWinContracts;
using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class DeadlineTrackerTests
{
    private static readonly JobTimeouts Timeouts = new()
    {
        StartExcelSeconds = 30,
        OpenWorkbookSeconds = 90,
        RefreshTotalSeconds = 1800,
        CalculationSeconds = 900,
        SaveSeconds = 90,
        CloseSeconds = 30,
    };

    [Theory]
    [InlineData("STARTING_EXCEL", 30)]
    [InlineData("OPENING_WORKBOOK", 90)]
    [InlineData("REFRESHING_CONNECTIONS", 1800)]
    [InlineData("REFRESHING_DATA_MODEL", 1800)]
    [InlineData("REFRESHING_PIVOTS", 1800)]
    [InlineData("CALCULATING", 900)]
    [InlineData("SAVING", 90)]
    [InlineData("SUCCEEDED", 30)]
    [InlineData("FAILED", 30)]
    public void Maps_known_phases_to_their_declared_timeout_field(string phase, int expectedSeconds)
    {
        var tracker = new DeadlineTracker(Timeouts);
        Assert.Equal(expectedSeconds, tracker.DeadlineSecondsFor(phase));
    }

    [Fact]
    public void Falls_back_to_the_default_for_unmapped_phases()
    {
        var tracker = new DeadlineTracker(Timeouts, defaultPhaseDeadlineSeconds: 55);
        Assert.Equal(55, tracker.DeadlineSecondsFor("VALIDATING"));
    }

    [Fact]
    public void Not_breached_before_the_deadline_elapses()
    {
        var tracker = new DeadlineTracker(Timeouts);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        var stillOk = tracker.IsBreached("STARTING_EXCEL", start, start.AddSeconds(29));

        Assert.False(stillOk);
    }

    [Fact]
    public void Breached_once_elapsed_time_exceeds_the_deadline()
    {
        var tracker = new DeadlineTracker(Timeouts);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        var breached = tracker.IsBreached("STARTING_EXCEL", start, start.AddSeconds(31));

        Assert.True(breached);
    }

    [Fact]
    public void Exactly_at_the_deadline_is_not_yet_breached()
    {
        var tracker = new DeadlineTracker(Timeouts);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        Assert.False(tracker.IsBreached("STARTING_EXCEL", start, start.AddSeconds(30)));
    }
}
