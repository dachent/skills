using System.Diagnostics;
using XlsxWinSupervisor;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>Launches the real XlsxWinSupervisor.exe as a child process against
/// a job/events/result path triple, per the file-path contract in README.md.</summary>
internal static class SupervisorRunner
{
    public sealed record RunResult(int ExitCode, string Stdout, string Stderr, TimeSpan Elapsed);

    public static RunResult Run(
        string jobPath,
        string eventsPath,
        string resultPath,
        TimeSpan hardTimeout,
        IReadOnlyDictionary<string, string>? extraEnv = null)
    {
        var startInfo = new ProcessStartInfo
        {
            FileName = BuiltExecutables.SupervisorExePath,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.ArgumentList.Add(jobPath);
        startInfo.ArgumentList.Add(eventsPath);
        startInfo.ArgumentList.Add(resultPath);

        // The worker is resolved by the supervisor via WorkerLauncher; point
        // it explicitly at this dev tree's built worker rather than relying
        // on directory-layout conventions that only hold for a published
        // side-by-side deployment.
        startInfo.Environment[WorkerLauncher.WorkerPathEnvVar] = BuiltExecutables.WorkerExePath;

        if (extraEnv is not null)
        {
            foreach (var (key, value) in extraEnv)
            {
                startInfo.Environment[key] = value;
            }
        }

        var stopwatch = Stopwatch.StartNew();
        using var process = Process.Start(startInfo)
            ?? throw new InvalidOperationException("Failed to start XlsxWinSupervisor process.");

        var stdoutTask = process.StandardOutput.ReadToEndAsync();
        var stderrTask = process.StandardError.ReadToEndAsync();

        var exited = process.WaitForExit((int)hardTimeout.TotalMilliseconds);
        if (!exited)
        {
            // Test-level safety net only: this should never trigger if the
            // supervisor's own Job-Object deadline enforcement is working.
            // Scoped to the exact process this test itself just launched --
            // never a by-name kill.
            try
            {
                process.Kill(entireProcessTree: true);
            }
            catch
            {
                // best-effort
            }

            throw new TimeoutException(
                $"XlsxWinSupervisor did not exit within the test's hard timeout of {hardTimeout}. " +
                "This indicates the supervisor's own deadline enforcement did not work.");
        }

        stopwatch.Stop();
        return new RunResult(process.ExitCode, stdoutTask.Result, stderrTask.Result, stopwatch.Elapsed);
    }
}
