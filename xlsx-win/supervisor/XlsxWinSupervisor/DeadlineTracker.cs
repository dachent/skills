using XlsxWinContracts;

namespace XlsxWinSupervisor;

public sealed record DeadlineSnapshot(
    string Phase,
    string Kind,
    int LimitSeconds,
    double ElapsedSeconds,
    double ConsumedRatio,
    bool Warning);

/// <summary>
/// Pure deadline calculation for phase breaches and active-clock snapshots.
/// No process or file I/O -- fully unit-testable with synthetic timestamps.
/// </summary>
public sealed class DeadlineTracker
{
    private readonly JobTimeouts _timeouts;
    private readonly int _defaultPhaseDeadlineSeconds;

    /// <param name="defaultPhaseDeadlineSeconds">Used for any state-machine
    /// phase that JobTimeouts.ForPhase does not map to a specific field (e.g.
    /// OPENING_WORKBOOK-adjacent bookkeeping phases this increment does not
    /// separately budget). Generous on purpose since it is a fallback, not the
    /// primary control.</param>
    public DeadlineTracker(JobTimeouts timeouts, int defaultPhaseDeadlineSeconds = 120)
    {
        _timeouts = timeouts;
        _defaultPhaseDeadlineSeconds = defaultPhaseDeadlineSeconds;
    }

    public int DeadlineSecondsFor(string phase) => _timeouts.ForPhase(phase) ?? _defaultPhaseDeadlineSeconds;

    /// <summary>Selects the clock with the least remaining time. Ties retain
    /// the supervisor's whole-job, inactivity, then phase breach-check order.</summary>
    public DeadlineSnapshot Snapshot(
        string currentPhase,
        DateTime startedUtc,
        DateTime phaseStartedUtc,
        DateTime lastActivityUtc,
        DateTime nowUtc)
    {
        var candidates = new[]
        {
            CreateSnapshot(currentPhase, "whole_job", _timeouts.WholeJobSeconds, startedUtc, nowUtc),
            CreateSnapshot(currentPhase, "inactivity", _timeouts.InactivitySeconds, lastActivityUtc, nowUtc),
            CreateSnapshot(currentPhase, "phase", DeadlineSecondsFor(currentPhase), phaseStartedUtc, nowUtc),
        };
        var active = candidates[0];
        for (var index = 1; index < candidates.Length; index++)
        {
            var remaining = candidates[index].LimitSeconds - candidates[index].ElapsedSeconds;
            var activeRemaining = active.LimitSeconds - active.ElapsedSeconds;
            if (remaining < activeRemaining)
            {
                active = candidates[index];
            }
        }
        return active;
    }

    private static DeadlineSnapshot CreateSnapshot(
        string phase,
        string kind,
        int limitSeconds,
        DateTime clockStartedUtc,
        DateTime nowUtc)
    {
        var elapsedSeconds = (nowUtc - clockStartedUtc).TotalSeconds;
        var consumedRatio = elapsedSeconds / limitSeconds;
        return new DeadlineSnapshot(phase, kind, limitSeconds, elapsedSeconds, consumedRatio, consumedRatio > 0.8);
    }

    /// <summary>True if more time has elapsed since lastTransitionUtc than the
    /// current phase's deadline allows, as of nowUtc.</summary>
    public bool IsBreached(string currentPhase, DateTime lastTransitionUtc, DateTime nowUtc)
    {
        var deadlineSeconds = DeadlineSecondsFor(currentPhase);
        return (nowUtc - lastTransitionUtc).TotalSeconds > deadlineSeconds;
    }
}
