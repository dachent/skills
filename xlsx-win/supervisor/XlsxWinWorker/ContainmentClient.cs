using System.Diagnostics;
using System.IO.Pipes;
using System.Security.Principal;
using XlsxWinContracts;

namespace XlsxWinWorker;

internal static class ContainmentClient
{
    public static ExcelProcessIdentity ConnectAndAwaitAcknowledgement(
        string pipeName,
        ExcelSession session,
        TimeSpan timeout)
    {
        var pid = session.ExcelProcessId ?? throw new InvalidOperationException("Excel PID is unavailable.");
        using var process = Process.GetProcessById(pid);
        var identity = new ExcelProcessIdentity
        {
            ExcelPid = pid,
            Hwnd = session.Gateway.Invoke("STARTING_EXCEL", "Application.Hwnd", () => (long)(int)session.App.Hwnd),
            CreationTimeUtcFileTime = process.StartTime.ToUniversalTime().ToFileTimeUtc(),
            ImagePath = process.MainModule?.FileName ?? throw new InvalidOperationException("Cannot read Excel image path."),
            SessionId = process.SessionId,
            User = WindowsIdentity.GetCurrent().Name,
        };

        using var pipe = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.WriteThrough);
        pipe.Connect(checked((int)timeout.TotalMilliseconds));
        FramedControl.Write(pipe, identity);
        var acknowledgement = FramedControl.Read<ContainmentAck>(pipe);
        if (!acknowledgement.Accepted)
            throw new InvalidOperationException($"Supervisor rejected Excel containment: {acknowledgement.Message}");
        return identity;
    }
}
