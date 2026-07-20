using System.Runtime.InteropServices;

namespace XlsxWinWorker;

[ComImport]
[Guid("00000016-0000-0000-C000-000000000046")]
[InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
internal interface IOleMessageFilter
{
    [PreserveSig]
    int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo);
    [PreserveSig]
    int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType);
    [PreserveSig]
    int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType);
}

internal sealed class ComMessageFilter : IOleMessageFilter
{
    private const int ServerCallIsHandled = 0;
    private const int ServerCallRejected = 1;
    private const int ServerCallRetryLater = 2;
    private const int PendingMsgWaitDefProcess = 2;
    private const int CancelCall = -1;
    public const int MaxRetryAttempts = 10;
    public const int MaxRejectedCallElapsedMilliseconds = 2000;
    private const int RetryDelayMilliseconds = 200;

    private static IOleMessageFilter? _previousFilter;
    private int _retryAttempts;
    private int _cumulativeRetryMilliseconds;

    public int RetryAttempts => _retryAttempts;
    public int CumulativeRetryMilliseconds => _cumulativeRetryMilliseconds;
    public void ResetRetryAttempts()
    {
        _retryAttempts = 0;
        _cumulativeRetryMilliseconds = 0;
    }

    public int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo) => ServerCallIsHandled;

    public int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType)
    {
        if (dwRejectType == ServerCallRejected) return CancelCall;
        if (dwRejectType != ServerCallRetryLater) return CancelCall;
        _retryAttempts++;
        if (_retryAttempts > MaxRetryAttempts || dwTickCount >= MaxRejectedCallElapsedMilliseconds) return CancelCall;
        _cumulativeRetryMilliseconds += RetryDelayMilliseconds;
        return RetryDelayMilliseconds;
    }

    public int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType) => PendingMsgWaitDefProcess;

    public static ComMessageFilter? Current { get; private set; }

    public static void Register()
    {
        if (Current is not null) throw new InvalidOperationException("COM message filter is already registered on this STA.");
        var filter = new ComMessageFilter();
        var hresult = NativeMethods.CoRegisterMessageFilter(filter, out var previous);
        Marshal.ThrowExceptionForHR(hresult);
        _previousFilter = previous;
        Current = filter;
    }

    public static void Revoke()
    {
        if (Current is null) return;
        var hresult = NativeMethods.CoRegisterMessageFilter(_previousFilter, out _);
        try { Marshal.ThrowExceptionForHR(hresult); }
        finally
        {
            Current = null;
            _previousFilter = null;
        }
    }
}
