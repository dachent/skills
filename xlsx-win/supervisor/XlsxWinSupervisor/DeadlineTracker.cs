using XlsxWinContracts;

namespace XlsxWinSupervisor;

/// <summary>
/// Pure phase-deadline calculation: given the job's declared timeouts, the
/// phase the worker last reported, and when that phase started, decide
/// whether the deadline for the current phase has been exceeded. No process
/// or file I/O -- fully unit-testable with synthetic timestamps.
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

    /// <summary>True if more time has elapsed since lastTransitionUtc than the
    /// current phase's deadline allows, as of nowUtc.</summary>
    public bool IsBreached(string currentPhase, DateTime lastTransitionUtc, DateTime nowUtc)
    {
        var deadlineSeconds = DeadlineSecondsFor(currentPhase);
        return (nowUtc - lastTransitionUtc).TotalSeconds > deadlineSeconds;
    }
}
