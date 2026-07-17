namespace XlsxWinContracts;

/// <summary>
/// Job state machine: the enumerated states, legal transitions, and terminal check.
///
/// This is a direct C# port of xlsx-win/v2/control_plane/state_machine.py.
/// It intentionally reuses the exact same state name strings as that file --
/// nothing here invents parallel vocabulary. Keep the two in sync by hand;
/// there is no shared source of truth between the Python and C# runtimes yet.
/// </summary>
public static class JobStates
{
    public static readonly IReadOnlyList<string> States = new[]
    {
        "QUEUED",
        "STAGING_INPUT",
        "INSPECTING_WORKBOOK",
        "SELECTING_BACKENDS",
        "STARTING_EXCEL",
        "OPENING_WORKBOOK",
        "APPLYING_EDITS",
        "UPDATING_LINKS",
        "REFRESHING_CONNECTIONS",
        "REFRESHING_DATA_MODEL",
        "REFRESHING_PIVOTS",
        "CALCULATING",
        "RUNNING_APPROVED_MACRO",
        "VALIDATING",
        "SAVING",
        "REOPEN_VALIDATION",
        "PUBLISHING",
        "SUCCEEDED",
        "FAILED",
        "TIMED_OUT",
        "CANCELLED",
    };

    public static readonly IReadOnlySet<string> TerminalStates = new HashSet<string>
    {
        "SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED",
    };

    private static readonly IReadOnlySet<string> AbortStates = new HashSet<string>
    {
        "FAILED", "TIMED_OUT", "CANCELLED",
    };

    // Non-abort states grouped into forward-only phases, in the same order and
    // grouping as the Python _PHASES tuple.
    private static readonly IReadOnlyList<IReadOnlySet<string>> Phases = new IReadOnlySet<string>[]
    {
        new HashSet<string> { "QUEUED" },
        new HashSet<string> { "STAGING_INPUT" },
        new HashSet<string> { "INSPECTING_WORKBOOK" },
        new HashSet<string> { "SELECTING_BACKENDS" },
        new HashSet<string> { "STARTING_EXCEL" },
        new HashSet<string> { "OPENING_WORKBOOK" },
        new HashSet<string>
        {
            "APPLYING_EDITS",
            "UPDATING_LINKS",
            "REFRESHING_CONNECTIONS",
            "REFRESHING_DATA_MODEL",
            "REFRESHING_PIVOTS",
            "CALCULATING",
            "RUNNING_APPROVED_MACRO",
        },
        new HashSet<string> { "VALIDATING" },
        new HashSet<string> { "SAVING" },
        new HashSet<string> { "REOPEN_VALIDATION" },
        new HashSet<string> { "PUBLISHING" },
        new HashSet<string> { "SUCCEEDED" },
    };

    private static int PhaseIndex(string state)
    {
        for (var i = 0; i < Phases.Count; i++)
        {
            if (Phases[i].Contains(state))
            {
                return i;
            }
        }

        throw new ArgumentException($"State '{state}' has no phase (is it an abort state?).");
    }

    public static bool IsTerminal(string state)
    {
        if (!States.Contains(state))
        {
            throw new ArgumentException($"Unknown state: '{state}'");
        }

        return TerminalStates.Contains(state);
    }

    public static bool CanTransition(string fromState, string toState)
    {
        if (!States.Contains(fromState))
        {
            throw new ArgumentException($"Unknown state: '{fromState}'");
        }

        if (!States.Contains(toState))
        {
            throw new ArgumentException($"Unknown state: '{toState}'");
        }

        if (fromState == toState)
        {
            return false;
        }

        if (IsTerminal(fromState))
        {
            return false;
        }

        if (AbortStates.Contains(toState))
        {
            return true;
        }

        return PhaseIndex(toState) >= PhaseIndex(fromState);
    }

    /// <summary>Return toState if the transition is legal, else throw.</summary>
    public static string Transition(string fromState, string toState)
    {
        if (!CanTransition(fromState, toState))
        {
            throw new InvalidOperationException(
                $"Illegal state transition: {fromState} -> {toState}.");
        }

        return toState;
    }
}
