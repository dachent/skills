using System.Diagnostics;
using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Safety gates every test in this project must apply, per the increment's
/// safety rules:
///
///  1. Refuse to run (skip) if an Excel process is already running on this
///     machine -- checked fresh at the start of every test, not just once.
///  2. Refuse to run (skip) unless XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS=1 is
///     set, so a plain `dotnet test` never launches real Excel.
///  5. After the test's own Excel usage, verify no EXCEL.EXE process
///     survives.
///
/// This never enumerates Excel processes in order to kill them -- only to
/// decide whether to skip (rule 1) or to verify cleanup happened (rule 5).
/// Actual termination is always Job-Object-based and PID-scoped; see
/// XlsxWinSupervisor.JobObjectHandle.
/// </summary>
public static class ExcelIntegrationGate
{
    public const string RunEnvVar = "XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS";

    /// <summary>Call at the very start of every test (constructor or first
    /// line of the test method). Skips the test if the opt-in env var is not
    /// set to "1", or if an Excel process is already running.</summary>
    public static void PreflightOrSkip()
    {
        var optedIn = Environment.GetEnvironmentVariable(RunEnvVar) == "1";
        Skip.IfNot(optedIn,
            $"Set {RunEnvVar}=1 to run real-Excel integration tests. See supervisor/README.md, " +
            "'Running the integration tests for real'.");

        var alreadyRunning = Process.GetProcessesByName("EXCEL");
        try
        {
            Skip.If(alreadyRunning.Length > 0,
                $"Refusing to run: {alreadyRunning.Length} EXCEL.EXE process(es) are already running on this " +
                "machine. Close all Excel windows and retry -- this test will not proceed alongside an " +
                "instance you may be using interactively.");
        }
        finally
        {
            foreach (var p in alreadyRunning)
            {
                p.Dispose();
            }
        }
    }

    /// <summary>Call at the end of every test. Polls for process teardown to
    /// finish, then asserts no EXCEL.EXE process remains.
    ///
    /// The wait window is generous (well beyond what a plain Quit() should
    /// need) because real verification on this machine surfaced a genuine,
    /// reproducible-in-pure-COM-automation finding: after a WorkbookConnection
    /// .Refresh() call (any connection type -- observed with both an OLEDB
    /// "Mashup"/Power-Query connection and a plain TEXT/QueryTable
    /// connection), Application.Quit() can take anywhere from ~5s to several
    /// minutes to actually let EXCEL.EXE exit, even though Quit() itself
    /// returns immediately and no modal dialog is present (confirmed via
    /// window enumeration) and the process is not deadlocked (one thread
    /// observed in a Running state, not blocked). This is an Excel-internal
    /// characteristic of this environment/session, not something this
    /// increment's code can wait out any faster -- see README.md, "Known
    /// limitation: connection-refresh shutdown latency".</summary>
    public static void AssertNoExcelProcessSurvives()
    {
        const int maxWaitSeconds = 180;
        const int pollMs = 500;

        for (var i = 0; i < maxWaitSeconds * 1000 / pollMs; i++)
        {
            using var probe = new ProcessNameProbe("EXCEL");
            if (probe.Count == 0)
            {
                return;
            }

            Thread.Sleep(pollMs);
        }

        using var finalProbe = new ProcessNameProbe("EXCEL");
        Assert.Equal(0, finalProbe.Count);
    }

    private sealed class ProcessNameProbe : IDisposable
    {
        private readonly Process[] _processes;

        public ProcessNameProbe(string name)
        {
            _processes = Process.GetProcessesByName(name);
        }

        public int Count => _processes.Length;

        public void Dispose()
        {
            foreach (var p in _processes)
            {
                p.Dispose();
            }
        }
    }
}
