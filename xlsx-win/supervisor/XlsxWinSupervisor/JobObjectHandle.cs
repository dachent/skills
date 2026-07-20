using System.ComponentModel;

namespace XlsxWinSupervisor;

/// <summary>
/// Thin, testable wrapper around the Win32 Job Object APIs. This is the
/// mechanism that makes force-termination reliable even when the worker's
/// STA thread is permanently wedged inside a COM call and cannot respond to
/// any cooperative shutdown request: TerminateJobObject kills every process
/// assigned to the job unconditionally, without requiring any of them to
/// cooperate.
///
/// Process-kill scope: this class only ever terminates processes explicitly
/// assigned to it via <see cref="AssignProcess"/> (the worker's own PID,
/// captured at launch, and the Excel PID the worker reports once it has
/// captured it from its own Application.Hwnd). It never enumerates processes
/// by name.
/// </summary>
public sealed class JobObjectHandle : IDisposable
{
    private IntPtr _handle;
    private bool _disposed;

    private JobObjectHandle(IntPtr handle)
    {
        _handle = handle;
    }

    /// <summary>Creates an unnamed Job Object with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    /// set, so that closing the last handle to the job (including on abnormal
    /// supervisor exit) also tears down every process still assigned to it.</summary>
    public static JobObjectHandle Create()
    {
        var handle = JobObjectNative.CreateJobObject(IntPtr.Zero, lpName: null);
        EnsureValidHandle(handle, nameof(JobObjectNative.CreateJobObject));

        var info = new JobObjectNative.JobObjectExtendedLimitInformation
        {
            BasicLimitInformation = new JobObjectNative.JobObjectBasicLimitInformation
            {
                LimitFlags = JobObjectNative.JobObjectLimitKillOnJobClose,
            },
        };

        var length = (uint)System.Runtime.InteropServices.Marshal.SizeOf<JobObjectNative.JobObjectExtendedLimitInformation>();
        var ok = JobObjectNative.SetInformationJobObject(
            handle,
            JobObjectNative.JobObjectExtendedLimitInformationClass,
            ref info,
            length);

        if (!ok)
        {
            var error = new Win32Exception();
            JobObjectNative.CloseHandle(handle);
            throw new InvalidOperationException(
                $"SetInformationJobObject failed while configuring JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE: {error.Message}", error);
        }

        return new JobObjectHandle(handle);
    }

    /// <summary>Assigns an already-open process handle to this job.</summary>
    public void AssignProcess(IntPtr processHandle)
    {
        ThrowIfDisposed();
        var ok = JobObjectNative.AssignProcessToJobObject(_handle, processHandle);
        if (!ok)
        {
            throw new InvalidOperationException(
                $"AssignProcessToJobObject failed: {new Win32Exception().Message}");
        }
    }

    /// <summary>Opens a process by PID with just enough access to assign it to
    /// this job and (later) terminate it, and assigns it. Used for the Excel
    /// process, whose PID the worker captures itself from Application.Hwnd and
    /// reports back over the JSONL event stream -- COM-activated out-of-process
    /// servers are launched by the OS's RPC activation service, not as a direct
    /// child of the worker process, so they do not automatically inherit the
    /// worker's job membership and must be assigned explicitly.
    ///
    /// Before assigning, verifies the PID still identifies an EXCEL.EXE
    /// process. This is not a by-name *enumeration* (it never scans the
    /// process list to find a target) -- it is an identity check on a PID
    /// this class was explicitly handed, guarding against the narrow window
    /// where Excel has already exited and the OS recycled that exact PID for
    /// an unrelated process before this call runs. A mismatch is treated as a
    /// hard failure (no assignment), never silently folded into the kill
    /// scope.</summary>
    public void AssignProcessById(int processId)
    {
        ThrowIfDisposed();

        if (!IsPlausiblyExcelProcess(processId, out var actualName))
        {
            throw new InvalidOperationException(
                $"Refusing to assign PID {processId} to the Job Object: it does not currently identify an " +
                $"EXCEL.EXE process (found '{actualName ?? "<no such process>"}' instead). This can happen if " +
                "Excel already exited and the OS reused the PID for an unrelated process in the narrow window " +
                "before this call.");
        }

        var handle = JobObjectNative.OpenProcess(
            JobObjectNative.ProcessTerminate | JobObjectNative.ProcessSetQuota,
            bInheritHandle: false,
            (uint)processId);

        if (handle == IntPtr.Zero)
        {
            throw new InvalidOperationException(
                $"OpenProcess({processId}) failed: {new Win32Exception().Message}");
        }

        try
        {
            AssignProcess(handle);
        }
        finally
        {
            JobObjectNative.CloseHandle(handle);
        }
    }

    /// <summary>Checks whether a PID currently identifies a process named
    /// "EXCEL" (i.e. EXCEL.EXE), using the standard process list rather than
    /// the job's own handle -- this is an identity check on one specific,
    /// already-known PID, not a scan for a target by name.</summary>
    internal static bool IsPlausiblyExcelProcess(int processId, out string? actualProcessName)
    {
        actualProcessName = null;
        try
        {
            using var process = System.Diagnostics.Process.GetProcessById(processId);
            actualProcessName = process.ProcessName;
            return string.Equals(process.ProcessName, "EXCEL", StringComparison.OrdinalIgnoreCase);
        }
        catch (ArgumentException)
        {
            // No process with this ID exists any more.
            return false;
        }
    }

    /// <summary>Kills every process currently assigned to this job, in one
    /// unconditional call. This is the only termination path this codebase
    /// uses -- never a by-name process enumeration/kill.</summary>
    public void Terminate(uint exitCode = 1)
    {
        ThrowIfDisposed();
        if (!JobObjectNative.TerminateJobObject(_handle, exitCode))
        {
            throw new InvalidOperationException($"TerminateJobObject failed: {new Win32Exception().Message}");
        }
    }

    public uint ActiveProcessCount()
    {
        ThrowIfDisposed();
        var accounting = new JobObjectNative.JobObjectBasicAccountingInformation();
        var length = (uint)System.Runtime.InteropServices.Marshal.SizeOf<JobObjectNative.JobObjectBasicAccountingInformation>();
        if (!JobObjectNative.QueryInformationJobObject(
                _handle,
                JobObjectNative.JobObjectBasicAccountingInformationClass,
                ref accounting,
                length,
                IntPtr.Zero))
        {
            throw new InvalidOperationException($"QueryInformationJobObject failed: {new Win32Exception().Message}");
        }
        return accounting.ActiveProcesses;
    }

    /// <summary>Throws a clear, specific exception if a Win32 handle-returning
    /// API failed (returned a null/invalid handle). Factored out so it can be
    /// unit-tested without making a real Win32 call.</summary>
    internal static void EnsureValidHandle(IntPtr handle, string apiName)
    {
        if (handle == IntPtr.Zero)
        {
            throw new InvalidOperationException(
                $"{apiName} failed and returned a null handle: {new Win32Exception().Message}");
        }
    }

    private void ThrowIfDisposed()
    {
        if (_disposed)
        {
            throw new ObjectDisposedException(nameof(JobObjectHandle));
        }
    }

    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;
        if (_handle != IntPtr.Zero)
        {
            JobObjectNative.CloseHandle(_handle);
            _handle = IntPtr.Zero;
        }
    }
}
