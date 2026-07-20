using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text.Json;

namespace XlsxWinSupervisor;

internal sealed class TelemetrySampler : IDisposable
{
    private readonly StreamWriter _writer;

    public TelemetrySampler(string eventsPath)
    {
        var path = eventsPath + ".telemetry.jsonl";
        _writer = new StreamWriter(new FileStream(path, FileMode.Create, FileAccess.Write, FileShare.Read)) { AutoFlush = true };
    }

    public void Sample(string phase, int workerPid, int? excelPid, string reason)
    {
        var performance = new PerformanceInformation { Size = Marshal.SizeOf<PerformanceInformation>() };
        if (!GetPerformanceInfo(ref performance, performance.Size))
            throw new InvalidOperationException("GetPerformanceInfo failed.");
        var pageSize = unchecked((long)performance.PageSize);
        _writer.WriteLine(JsonSerializer.Serialize(new
        {
            schema_version = "1.0",
            timestamp = DateTimeOffset.UtcNow,
            phase,
            reason,
            system_commit_total_bytes = unchecked((long)performance.CommitTotal) * pageSize,
            system_commit_limit_bytes = unchecked((long)performance.CommitLimit) * pageSize,
            worker = ProcessSample(workerPid),
            excel = excelPid is int pid ? ProcessSample(pid) : null,
        }));
    }

    private static object? ProcessSample(int processId)
    {
        try
        {
            using var process = Process.GetProcessById(processId);
            process.Refresh();
            return new
            {
                pid = processId,
                creation_time_utc_filetime = process.StartTime.ToUniversalTime().ToFileTimeUtc(),
                private_bytes = process.PrivateMemorySize64,
                working_set_bytes = process.WorkingSet64,
                handle_count = process.HandleCount,
                session_id = process.SessionId,
            };
        }
        catch (ArgumentException)
        {
            return null;
        }
    }

    public void Dispose() => _writer.Dispose();

    [StructLayout(LayoutKind.Sequential)]
    private struct PerformanceInformation
    {
        public int Size;
        public IntPtr CommitTotal, CommitLimit, CommitPeak, PhysicalTotal, PhysicalAvailable;
        public IntPtr SystemCache, KernelTotal, KernelPaged, KernelNonpaged, PageSize;
        public int HandleCount, ProcessCount, ThreadCount;
    }

    [DllImport("psapi.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetPerformanceInfo(ref PerformanceInformation performanceInformation, int size);
}
