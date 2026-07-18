using System.Runtime.InteropServices;

namespace XlsxWinWorker;

/// <summary>
/// The standard, well-known IOleMessageFilter COM interop pattern for handling
/// SERVERCALL_RETRYLATER / RPC_E_CALL_REJECTED responses from a busy Excel COM
/// server, documented in numerous Microsoft KB articles about Office
/// automation hangs. This exact interface shape (GUID, method signatures) is
/// load-bearing -- COM identifies it by IID, not .NET type identity, so it
/// must match the published shape verbatim; it is not this codebase's to
/// redesign.
/// </summary>
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

/// <summary>
/// Registered on the worker's STA thread (see Program.cs.Main) so a
/// transient "server busy" response from Excel (SERVERCALL_RETRYLATER) is
/// retried with a short bounded backoff instead of surfacing immediately as
/// an opaque COM exception, and a genuinely rejected call
/// (SERVERCALL_REJECTED) fails fast instead of retrying something that will
/// never succeed.
///
/// Bound: up to <see cref="MaxRetryAttempts"/> (10) RETRYLATER responses,
/// each backed off by a short, fixed delay
/// (<see cref="RetryDelayMilliseconds"/>, 200ms), before giving up and
/// returning -1 (cancel the call) so the caller gets a clear COM exception
/// rather than an infinite retry loop.
///
/// The counter is reset once per job step (see StepRunner.Run), not per
/// individual outgoing COM call and not once for the whole job. A single
/// step can make many outgoing COM calls; resetting per-step is what lets
/// each step's own result message report "how many retries did *this* step
/// need" (see StepRunner's AppendRetrySuffix), which is the visibility the
/// acceptance criteria ask for. This is a deliberate, documented choice, not
/// an accident of implementation convenience.
/// </summary>
internal sealed class ComMessageFilter : IOleMessageFilter
{
    // IOleMessageFilter's own well-known constants (oleidl.h SERVERCALL_*/
    // PENDINGMSG_*): not exposed by any .NET base class library type, so
    // hand-copied here the same way ExcelConstants.cs hand-copies Excel's own
    // late-bound enum values.
    private const int ServerCallIsHandled = 0;
    private const int ServerCallRejected = 1;
    private const int ServerCallRetryLater = 2;
    private const int PendingMsgWaitDefProcess = 2;
    private const int CancelCall = -1;

    public const int MaxRetryAttempts = 10;
    private const int RetryDelayMilliseconds = 200;

    private int _retryAttempts;

    /// <summary>Number of RETRYLATER responses handled since the last
    /// <see cref="ResetRetryAttempts"/> call, whether or not the bound was
    /// exceeded.</summary>
    public int RetryAttempts => _retryAttempts;

    /// <summary>Call at the start of each job step so that step's own result
    /// message reports only that step's own retries, not a running total
    /// across the whole job. See StepRunner.Run.</summary>
    public void ResetRetryAttempts() => _retryAttempts = 0;

    public int HandleInComingCall(int dwCallType, IntPtr hTaskCaller, int dwTickCount, IntPtr lpInterfaceInfo) =>
        ServerCallIsHandled;

    public int RetryRejectedCall(IntPtr hTaskCallee, int dwTickCount, int dwRejectType)
    {
        if (dwRejectType == ServerCallRejected)
        {
            // Not retryable -- fail immediately rather than retrying a call
            // the server has explicitly refused.
            return CancelCall;
        }

        if (dwRejectType == ServerCallRetryLater)
        {
            _retryAttempts++;
            if (_retryAttempts > MaxRetryAttempts)
            {
                // Bound exceeded: give up so the caller sees a clear COM
                // exception instead of retrying indefinitely.
                return CancelCall;
            }

            return RetryDelayMilliseconds;
        }

        // Unrecognized reject type: fail closed rather than retry something
        // this filter does not understand.
        return CancelCall;
    }

    public int MessagePending(IntPtr hTaskCallee, int dwTickCount, int dwPendingType) =>
        PendingMsgWaitDefProcess;

    /// <summary>The single filter instance registered for this process's STA
    /// thread, if any. Null before <see cref="Register"/> and after
    /// <see cref="Revoke"/>. StepRunner reads this to reset/inspect the retry
    /// counter around each step.</summary>
    public static ComMessageFilter? Current { get; private set; }

    /// <summary>Registers this filter via CoRegisterMessageFilter. Must be
    /// called on the STA thread the filter should apply to (Program.cs's
    /// Main, immediately after WorkerArgs parsing succeeds -- before Excel is
    /// ever started), and paired with <see cref="Revoke"/> on every exit
    /// path.</summary>
    public static void Register()
    {
        var filter = new ComMessageFilter();
        NativeMethods.CoRegisterMessageFilter(filter, out _);
        Current = filter;
    }

    /// <summary>Revokes the message filter (registers null), restoring
    /// default COM behavior. Safe to call even if Register was never
    /// called.</summary>
    public static void Revoke()
    {
        if (Current is null)
        {
            return;
        }

        NativeMethods.CoRegisterMessageFilter(null!, out _);
        Current = null;
    }
}
