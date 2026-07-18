using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

[Collection("WorkerLauncherEnvVar")] // serialize: these tests mutate a process-wide env var
public class WorkerLauncherTests : IDisposable
{
    private readonly string _tempDir;

    public WorkerLauncherTests()
    {
        _tempDir = Path.Combine(Path.GetTempPath(), "xlsxwin-launcher-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tempDir);
        Environment.SetEnvironmentVariable(WorkerLauncher.WorkerPathEnvVar, null);
    }

    public void Dispose()
    {
        Environment.SetEnvironmentVariable(WorkerLauncher.WorkerPathEnvVar, null);
        try
        {
            Directory.Delete(_tempDir, recursive: true);
        }
        catch
        {
            // best-effort cleanup
        }
    }

    [Fact]
    public void Env_var_override_is_used_when_the_file_exists()
    {
        var fakeExe = Path.Combine(_tempDir, "XlsxWinWorker.exe");
        File.WriteAllText(fakeExe, "not a real exe, just needs to exist");

        Environment.SetEnvironmentVariable(WorkerLauncher.WorkerPathEnvVar, fakeExe);

        var resolved = WorkerLauncher.ResolveWorkerExePath();

        Assert.Equal(fakeExe, resolved);
    }

    [Fact]
    public void Env_var_override_pointing_at_a_missing_file_throws_clearly()
    {
        var missing = Path.Combine(_tempDir, "does-not-exist.exe");
        Environment.SetEnvironmentVariable(WorkerLauncher.WorkerPathEnvVar, missing);

        var ex = Assert.Throws<FileNotFoundException>(() => WorkerLauncher.ResolveWorkerExePath());

        Assert.Contains(WorkerLauncher.WorkerPathEnvVar, ex.Message);
    }
}
