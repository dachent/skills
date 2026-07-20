using System.Diagnostics;
using XlsxWinContracts;
using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class SupervisorCleanupGraceTests
{
    [Fact]
    public void Clean_exit_accepts_a_delayed_natural_owned_process_exit()
    {
        var resultPath = WriteTrustedSuccessResult();
        try
        {
            using var worker = StartCompletedWorker();
            using var process = StartPingProcess(3);
            using var job = JobObjectHandle.Create();
            job.AssignProcess(process.Handle);

            var exitCode = Program.HandleCleanExit(
                job, worker, workerExitCode: 0, new JobManifest { IdempotencyKey = "cleanup-grace-test" },
                resultPath, shutdownSeconds: 5);

            var result = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal(0, exitCode);
            Assert.True(process.HasExited);
            Assert.True(result.Ok);
            Assert.Equal("SUCCEEDED", result.FinalState);
            Assert.Contains(result.Invariants, invariant =>
                invariant.Name == "supervisor_owned_processes_zero" && invariant.Passed);
        }
        finally
        {
            File.Delete(resultPath);
        }
    }

    [Fact]
    public void Clean_exit_preserves_success_after_verified_residual_termination()
    {
        var resultPath = WriteTrustedSuccessResult();
        try
        {
            using var worker = StartCompletedWorker();
            using var process = StartPingProcess(30);
            using var job = JobObjectHandle.Create();
            job.AssignProcess(process.Handle);

            var exitCode = Program.HandleCleanExit(
                job, worker, workerExitCode: 0, new JobManifest { IdempotencyKey = "cleanup-grace-test" },
                resultPath, shutdownSeconds: 1);

            var result = ResultDocument.Parse(File.ReadAllText(resultPath));
            Assert.Equal(0, exitCode);
            Assert.True(process.HasExited);
            Assert.True(result.Ok);
            Assert.Equal("SUCCEEDED", result.FinalState);
            var invariant = Assert.Single(result.Invariants, invariant =>
                invariant.Name == "supervisor_owned_processes_zero");
            Assert.True(invariant.Passed);
            Assert.Contains("forced_residual_cleanup=true", invariant.Message);
            Assert.Contains("termination_verified=true", invariant.Message);
            var originalCount = System.Text.RegularExpressions.Regex.Match(
                invariant.Message!, @"original_active_owned_processes=(\d+)");
            Assert.True(originalCount.Success);
            Assert.True(uint.Parse(originalCount.Groups[1].Value) > 0);
        }
        finally
        {
            File.Delete(resultPath);
        }
    }

    [Fact]
    public void Residual_cleanup_decision_fails_closed_when_termination_is_not_verified()
    {
        var workerResult = TrustedSuccessResult();

        var result = Program.BuildResidualCleanupResult(
            workerResult, originalActive: 2, cleanup: false,
            "termination_verified=false; active_owned_processes=2");

        Assert.False(result.Ok);
        Assert.Equal("FAILED", result.FinalState);
        Assert.Contains(result.Steps, step =>
            step.Error?.Code == "OWNED_PROCESS_CLEANUP_REQUIRED"
            && step.Error.Details.TryGetValue("cleanup_verified", out var value)
            && value is false);
        Assert.Contains(result.Invariants, invariant =>
            invariant.Name == "supervisor_owned_process_cleanup" && !invariant.Passed);
    }

    private static string WriteTrustedSuccessResult()
    {
        var path = Path.Combine(Path.GetTempPath(), $"xlsx-win-cleanup-grace-{Guid.NewGuid():N}.json");
        var result = TrustedSuccessResult();
        File.WriteAllText(path, result.ToJson());
        return path;
    }

    private static ResultDocument TrustedSuccessResult() =>
        ResultDocument.Build(
            "cleanup-grace-run", "cleanup-grace-test", "SUCCEEDED",
            new List<StepResult>
            {
                new() { StepIndex = 0, Type = "test", Status = "succeeded" },
            });

    private static Process StartCompletedWorker()
    {
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = Path.Combine(Environment.SystemDirectory, "cmd.exe"),
            Arguments = "/d /s /c exit 0",
            UseShellExecute = false,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException("Failed to start the benign completed worker process.");
        Assert.True(process.WaitForExit(5_000));
        return process;
    }

    private static Process StartPingProcess(int count)
    {
        var process = Process.Start(new ProcessStartInfo
        {
            FileName = Path.Combine(Environment.SystemDirectory, "cmd.exe"),
            Arguments = $"/d /s /c \"ping 127.0.0.1 -n {count} > nul\"",
            UseShellExecute = false,
            CreateNoWindow = true,
        });
        return process ?? throw new InvalidOperationException("Failed to start the benign cleanup-grace test process.");
    }
}
