using System.Diagnostics;
using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class JobObjectAccountingTests
{
    [Fact]
    public void Assigned_process_is_counted_and_termination_reaches_zero()
    {
        var command = Path.Combine(Environment.SystemDirectory, "cmd.exe");
        using var process = Process.Start(new ProcessStartInfo
        {
            FileName = command,
            Arguments = "/d /s /c \"ping 127.0.0.1 -n 30 > nul\"",
            UseShellExecute = false,
            CreateNoWindow = true,
        }) ?? throw new InvalidOperationException("Failed to start the benign ownership-test process.");

        try
        {
            using var job = JobObjectHandle.Create();
            job.AssignProcess(process.Handle);
            Assert.Equal(1u, job.ActiveProcessCount());

            job.Terminate(23);
            Assert.True(process.WaitForExit(5_000));
            Assert.True(SpinWait.SpinUntil(() => job.ActiveProcessCount() == 0, 5_000));
        }
        finally
        {
            if (!process.HasExited)
                process.Kill(entireProcessTree: true);
        }
    }
}
