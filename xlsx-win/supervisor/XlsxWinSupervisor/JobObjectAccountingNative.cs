using System.Runtime.InteropServices;

namespace XlsxWinSupervisor;

internal static partial class JobObjectNative
{
    public const int JobObjectBasicAccountingInformationClass = 1;

    [StructLayout(LayoutKind.Sequential)]
    public struct JobObjectBasicAccountingInformation
    {
        public long TotalUserTime;
        public long TotalKernelTime;
        public long ThisPeriodTotalUserTime;
        public long ThisPeriodTotalKernelTime;
        public uint TotalPageFaultCount;
        public uint TotalProcesses;
        public uint ActiveProcesses;
        public uint TotalTerminatedProcesses;
    }

    [LibraryImport("kernel32.dll", SetLastError = true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    public static partial bool QueryInformationJobObject(
        IntPtr hJob,
        int jobObjectInformationClass,
        ref JobObjectBasicAccountingInformation jobObjectInformation,
        uint jobObjectInformationLength,
        IntPtr returnLength);
}
