using System.Runtime.InteropServices;

namespace XlsxWinWorker;

internal static partial class NativeMethods
{
    [LibraryImport("user32.dll")]
    internal static partial uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    // Used only by the test-only crash simulation in Program.cs
    // (XLSXWIN_TEST_SIMULATE_CRASH_AFTER_STEP). SEM_FAILCRITICALERRORS
    // (0x0001) + SEM_NOGPFAULTERRORBOX (0x0002) suppress the OS's "program
    // has stopped working" Windows Error Reporting dialog (and any
    // registered JIT-debugger prompt) for this process before it deliberately
    // throws an unhandled exception -- the standard mechanism unattended/CI
    // processes use so a genuine crash terminates silently instead of
    // surfacing blocking UI. This exists specifically so that integration
    // test never risks putting an unclosable dialog on a real, actively-used
    // desktop (safety rule: no new hang risk). Never called on any
    // production code path -- only from the test-only crash branch.
    [LibraryImport("kernel32.dll")]
    internal static partial uint SetErrorMode(uint uMode);

    internal const uint SemFailCriticalErrors = 0x0001;
    internal const uint SemNoGpFaultErrorBox = 0x0002;

    // Standard COM message-filter registration (Ole32.dll), used by
    // ComMessageFilter.Register/Revoke to install/remove the IOleMessageFilter
    // documented there (RFC-issue #72's IMessageFilter scope). Classic
    // [DllImport] rather than [LibraryImport]: the source-generated marshaling
    // behind LibraryImport does not support a COM-interface `out` parameter
    // like this one.
    [DllImport("Ole32.dll")]
    internal static extern int CoRegisterMessageFilter(IOleMessageFilter newFilter, out IOleMessageFilter oldFilter);
}
