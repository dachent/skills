using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

namespace XlsxWinSupervisor;

internal sealed class SuspendedWorker : IDisposable
{
    private const uint CreateSuspended = 0x00000004;
    private const uint CreateNoWindow = 0x08000000;
    private IntPtr _processHandle;
    private IntPtr _threadHandle;

    private SuspendedWorker(int processId, IntPtr processHandle, IntPtr threadHandle)
    {
        ProcessId = processId;
        _processHandle = processHandle;
        _threadHandle = threadHandle;
    }

    public int ProcessId { get; }
    public IntPtr ProcessHandle => _processHandle;

    public int ExitCode
    {
        get
        {
            if (!GetExitCodeProcess(_processHandle, out var exitCode))
                throw new InvalidOperationException($"GetExitCodeProcess failed: {new Win32Exception().Message}");
            if (exitCode == StillActive)
                throw new InvalidOperationException("Worker exit code was requested while the process was still active.");
            return unchecked((int)exitCode);
        }
    }

    private const uint StillActive = 259;

    public static SuspendedWorker Create(string executable, IReadOnlyList<string> arguments)
    {
        var commandLine = new StringBuilder(Quote(executable));
        foreach (var argument in arguments) commandLine.Append(' ').Append(Quote(argument));
        var startup = new StartupInfo { Cb = Marshal.SizeOf<StartupInfo>() };
        if (!CreateProcessW(executable, commandLine, IntPtr.Zero, IntPtr.Zero, false,
                CreateSuspended | CreateNoWindow, IntPtr.Zero, null, ref startup, out var info))
            throw new InvalidOperationException($"CreateProcessW(CREATE_SUSPENDED) failed: {new Win32Exception().Message}");
        return new SuspendedWorker(unchecked((int)info.ProcessId), info.Process, info.Thread);
    }

    public Process Resume()
    {
        if (ResumeThread(_threadHandle) == uint.MaxValue)
            throw new InvalidOperationException($"ResumeThread failed: {new Win32Exception().Message}");
        return Process.GetProcessById(ProcessId);
    }

    internal static string Quote(string value)
    {
        if (value.Length > 0 && !value.Any(character => char.IsWhiteSpace(character) || character == '\"')) return value;
        var result = new StringBuilder("\"");
        var backslashes = 0;
        foreach (var character in value)
        {
            if (character == '\\')
            {
                backslashes++;
                continue;
            }
            if (character == '\"')
            {
                result.Append('\\', backslashes * 2 + 1).Append('\"');
                backslashes = 0;
                continue;
            }
            result.Append('\\', backslashes).Append(character);
            backslashes = 0;
        }
        result.Append('\\', backslashes * 2).Append('\"');
        return result.ToString();
    }

    public void Dispose()
    {
        if (_threadHandle != IntPtr.Zero) { CloseHandle(_threadHandle); _threadHandle = IntPtr.Zero; }
        if (_processHandle != IntPtr.Zero) { CloseHandle(_processHandle); _processHandle = IntPtr.Zero; }
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    private struct StartupInfo
    {
        public int Cb;
        public string? Reserved;
        public string? Desktop;
        public string? Title;
        public int X, Y, XSize, YSize, XCountChars, YCountChars, FillAttribute, Flags;
        public short ShowWindow, Reserved2;
        public IntPtr Reserved2Pointer, StdInput, StdOutput, StdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessInformation
    {
        public IntPtr Process, Thread;
        public uint ProcessId, ThreadId;
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CreateProcessW(string applicationName, StringBuilder commandLine,
        IntPtr processAttributes, IntPtr threadAttributes, [MarshalAs(UnmanagedType.Bool)] bool inheritHandles,
        uint creationFlags, IntPtr environment, string? currentDirectory, ref StartupInfo startupInfo,
        out ProcessInformation processInformation);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern uint ResumeThread(IntPtr thread);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool GetExitCodeProcess(IntPtr process, out uint exitCode);

    [DllImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    private static extern bool CloseHandle(IntPtr handle);
}
