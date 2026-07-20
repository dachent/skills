using System.Runtime.InteropServices;

namespace XlsxWinWorker;

internal static partial class NativeMethods
{
    [LibraryImport("user32.dll")]
    internal static partial uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);

    [LibraryImport("kernel32.dll")]
    internal static partial uint SetErrorMode(uint uMode);

    internal const uint SemFailCriticalErrors = 0x0001;
    internal const uint SemNoGpFaultErrorBox = 0x0002;

    [DllImport("Ole32.dll")]
    internal static extern int CoRegisterMessageFilter(IOleMessageFilter? newFilter, out IOleMessageFilter? oldFilter);
}
