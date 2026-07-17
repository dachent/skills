using System.Runtime.InteropServices;

namespace XlsxWinWorker;

internal static partial class NativeMethods
{
    [LibraryImport("user32.dll")]
    internal static partial uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
