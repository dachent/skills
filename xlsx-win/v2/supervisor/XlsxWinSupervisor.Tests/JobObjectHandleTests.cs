using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class JobObjectHandleTests
{
    [Fact]
    public void EnsureValidHandle_throws_a_clear_error_for_a_null_handle()
    {
        // Exercises the failure-handling logic that CreateJobObject's wrapper
        // relies on without needing to force a real CreateJobObject failure
        // (which is not reliably inducible in a test process).
        var ex = Assert.Throws<InvalidOperationException>(
            () => JobObjectHandle.EnsureValidHandle(IntPtr.Zero, "CreateJobObject"));

        Assert.Contains("CreateJobObject", ex.Message);
        Assert.Contains("failed", ex.Message, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void EnsureValidHandle_does_not_throw_for_a_non_null_handle()
    {
        JobObjectHandle.EnsureValidHandle(new IntPtr(1), "CreateJobObject");
    }

    [Fact]
    public void Create_returns_a_usable_disposable_handle()
    {
        // CreateJobObject itself is just a benign OS call (creates an unnamed
        // kernel object) -- no process is spawned and no Excel is touched, so
        // this is safe to run unconditionally in a plain `dotnet test`.
        using var job = JobObjectHandle.Create();
    }

    [Fact]
    public void Operations_after_dispose_throw_ObjectDisposedException()
    {
        var job = JobObjectHandle.Create();
        job.Dispose();

        Assert.Throws<ObjectDisposedException>(() => job.AssignProcess(IntPtr.Zero));
    }

    [Fact]
    public void Dispose_is_idempotent()
    {
        var job = JobObjectHandle.Create();
        job.Dispose();
        job.Dispose(); // must not throw
    }

    [Fact]
    public void AssignProcessById_refuses_a_pid_that_does_not_identify_excel()
    {
        // This test process itself is a real, live PID -- definitely not
        // EXCEL.EXE -- exercising the identity check without needing Excel or
        // any process spawning. Guards against the PID-reuse window: this
        // must never silently fold an unrelated process into the kill scope.
        using var job = JobObjectHandle.Create();
        var thisProcessId = Environment.ProcessId;

        var ex = Assert.Throws<InvalidOperationException>(() => job.AssignProcessById(thisProcessId));

        Assert.Contains("EXCEL", ex.Message);
        Assert.Contains(thisProcessId.ToString(), ex.Message);
    }

    [Fact]
    public void AssignProcessById_refuses_a_pid_that_no_longer_exists()
    {
        using var job = JobObjectHandle.Create();

        // PID 0 is reserved (System Idle Process on Windows) and never a
        // process GetProcessById can open as an ordinary process; using a
        // clearly-invalid PID keeps this deterministic without depending on
        // exact process-table state.
        var ex = Assert.Throws<InvalidOperationException>(() => job.AssignProcessById(int.MaxValue));

        Assert.Contains("EXCEL", ex.Message);
    }

    [Fact]
    public void IsPlausiblyExcelProcess_reports_the_actual_process_name_on_mismatch()
    {
        var isExcel = JobObjectHandle.IsPlausiblyExcelProcess(Environment.ProcessId, out var actualName);

        Assert.False(isExcel);
        Assert.NotNull(actualName);
    }
}
