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
    [InlineData("COMPOSITE_PREFLIGHT", 120)]
    [InlineData("APPLYING_EDITS", 1800)]
    [InlineData("REFRESHING_CONNECTIONS", 1800)]
    [InlineData("REFRESHING_DATA_MODEL", 1800)]
    [InlineData("REFRESHING_PIVOTS", 600)]
    [InlineData("CALCULATING", 900)]
    [InlineData("SAVING", 90)]
    [InlineData("REOPENING", 600)]
    [InlineData("VALIDATING", 600)]
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
        Assert.Equal(55, tracker.DeadlineSecondsFor("UNKNOWN_PHASE"));
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

    [Theory]
    [InlineData(23.9, false)]
    [InlineData(24.0, false)]
    [InlineData(24.1, true)]
    public void Active_phase_deadline_warns_only_above_eighty_percent(double elapsedSeconds, bool expectedWarning)
    {
        var tracker = new DeadlineTracker(Timeouts);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        var now = start.AddSeconds(elapsedSeconds);

        var snapshot = tracker.Snapshot("STARTING_EXCEL", start, start, now, now);

        Assert.Equal("STARTING_EXCEL", snapshot.Phase);
        Assert.Equal("phase", snapshot.Kind);
        Assert.Equal(30, snapshot.LimitSeconds);
        Assert.Equal(elapsedSeconds, snapshot.ElapsedSeconds, 6);
        Assert.Equal(elapsedSeconds / 30, snapshot.ConsumedRatio, 6);
        Assert.Equal(expectedWarning, snapshot.Warning);
    }

    [Fact]
    public void Active_deadline_uses_the_default_limit_for_an_unknown_phase()
    {
        var tracker = new DeadlineTracker(Timeouts, defaultPhaseDeadlineSeconds: 100);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        var now = start.AddSeconds(80);

        var atThreshold = tracker.Snapshot("UNKNOWN_PHASE", start, start, now, now);
        var aboveThreshold = tracker.Snapshot("UNKNOWN_PHASE", start, start, now, now.AddTicks(1));

        Assert.Equal("phase", atThreshold.Kind);
        Assert.Equal(100, atThreshold.LimitSeconds);
        Assert.False(atThreshold.Warning);
        Assert.True(aboveThreshold.Warning);
    }

    [Fact]
    public void Active_deadline_selects_the_most_imminent_clock()
    {
        var timeouts = new JobTimeouts
        {
            WholeJobSeconds = 100,
            InactivitySeconds = 100,
            StartExcelSeconds = 100,
        };
        var tracker = new DeadlineTracker(timeouts);
        var now = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);

        var wholeJob = tracker.Snapshot("STARTING_EXCEL", now.AddSeconds(-90), now.AddSeconds(-10), now, now);
        var inactivity = tracker.Snapshot("STARTING_EXCEL", now.AddSeconds(-10), now.AddSeconds(-10), now.AddSeconds(-90), now);
        var phase = tracker.Snapshot("STARTING_EXCEL", now.AddSeconds(-10), now.AddSeconds(-90), now, now);

        Assert.Equal("whole_job", wholeJob.Kind);
        Assert.Equal(90, wholeJob.ElapsedSeconds);
        Assert.Equal("inactivity", inactivity.Kind);
        Assert.Equal(90, inactivity.ElapsedSeconds);
        Assert.Equal("phase", phase.Kind);
        Assert.Equal(90, phase.ElapsedSeconds);
    }

    [Fact]
    public void Active_deadline_ties_follow_existing_breach_precedence()
    {
        var timeouts = new JobTimeouts
        {
            WholeJobSeconds = 100,
            InactivitySeconds = 100,
            StartExcelSeconds = 100,
        };
        var tracker = new DeadlineTracker(timeouts);
        var start = new DateTime(2026, 1, 1, 0, 0, 0, DateTimeKind.Utc);
        var now = start.AddSeconds(90);

        var snapshot = tracker.Snapshot("STARTING_EXCEL", start, start, start, now);

        Assert.Equal("whole_job", snapshot.Kind);
    }
}
