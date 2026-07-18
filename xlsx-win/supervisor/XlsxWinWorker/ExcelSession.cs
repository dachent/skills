using System.Diagnostics;
using System.Runtime.InteropServices;

namespace XlsxWinWorker;

/// <summary>
/// Owns one Excel.Application COM instance for the lifetime of one job. Sets
/// the dialog-prevention properties from RFC 0002 decision 7 immediately on
/// start, and exposes the Excel process's own PID (captured from the
/// Application's Hwnd, per RFC 0002 decision 8 -- never a blind process-name
/// enumeration).
///
/// Uses late-bound `dynamic` COM (Type.GetTypeFromProgID("Excel.Application"))
/// rather than the Microsoft.Office.Interop.Excel PIA: that NuGet package's
/// current release depends on separate "office" (Microsoft.Office.Core) and
/// "Microsoft.Vbe.Interop" primary interop assemblies that are not published
/// to NuGet and are not present on this machine outside the GAC-based Office
/// PIA install path, so early-bound interop failed to build for real friction
/// reasons, not just version-pinning pickiness. Late-bound dynamic COM avoids
/// this whole dependency chain and works against any installed Excel version.
///
/// Important, empirically-discovered behavior (see README.md, "Known
/// limitation: connection-refresh shutdown latency"): Application.Quit()
/// returns almost immediately even when the underlying EXCEL.EXE process
/// itself goes on to take anywhere from seconds to several minutes to
/// actually exit -- observed specifically after a WorkbookConnection.Refresh()
/// call. If this class simply called Quit() and returned, the worker
/// process would exit "cleanly" while EXCEL.EXE kept running orphaned, and
/// the supervisor would never know to kill it (its phase-deadline tracking
/// only fires while the worker process is still alive). So
/// <see cref="CloseAndWait"/> blocks the worker on this exact PID exiting,
/// with no internal cutoff -- the supervisor's own phase-deadline
/// enforcement (mapped to close_seconds for the terminal SUCCEEDED/FAILED
/// phase) is the single source of truth for how long that's allowed to take,
/// and its Job Object kill reliably reaches this PID once assigned.
/// </summary>
internal sealed class ExcelSession : IDisposable
{
    private dynamic? _app;
    private dynamic? _workbook;
    private int? _excelProcessId;
    private bool _disposed;

    public dynamic App => _app ?? throw new InvalidOperationException("Excel has not been started.");

    public dynamic? Workbook => _workbook;

    /// <summary>Starts Excel and applies the dialog-prevention properties.
    /// Returns the Excel process's own PID.</summary>
    public int Start()
    {
        var excelType = Type.GetTypeFromProgID("Excel.Application")
            ?? throw new InvalidOperationException(
                "The 'Excel.Application' ProgID is not registered on this machine. Is Excel installed?");

        _app = Activator.CreateInstance(excelType)
            ?? throw new InvalidOperationException("Activator.CreateInstance(Excel.Application) returned null.");

        _app.Visible = false;
        _app.DisplayAlerts = false;
        _app.AskToUpdateLinks = false;
        _app.AutomationSecurity = ExcelConstants.MsoAutomationSecurityForceDisable;

        _excelProcessId = CaptureExcelProcessId();
        return _excelProcessId.Value;
    }

    /// <summary>Reads back the three dialog-prevention properties. Used by the
    /// integration test that proves (via COM readback) they are actually set,
    /// not just assumed.</summary>
    public (bool DisplayAlerts, bool AskToUpdateLinks, int AutomationSecurity) ReadDialogPreventionState()
    {
        var app = App;
        return ((bool)app.DisplayAlerts, (bool)app.AskToUpdateLinks, (int)app.AutomationSecurity);
    }

    public int CaptureExcelProcessId()
    {
        var hwnd = new IntPtr((int)App.Hwnd);
        NativeMethods.GetWindowThreadProcessId(hwnd, out var pid);
        return unchecked((int)pid);
    }

    public dynamic Open(string workbookPath, bool readOnly, bool updateLinks)
    {
        var updateLinksValue = updateLinks ? ExcelConstants.UpdateLinksAlways : ExcelConstants.UpdateLinksNever;
        _workbook = App.Workbooks.Open(workbookPath, updateLinksValue, readOnly);
        return _workbook;
    }

    public void SaveAs(string outputPath)
    {
        var workbook = _workbook ?? throw new InvalidOperationException("No workbook is open.");
        workbook.SaveAs(outputPath);
    }

    /// <summary>Closes the workbook, quits Excel, and then blocks until the
    /// captured Excel PID has actually exited -- no internal timeout. Call
    /// this explicitly (not just via Dispose/using) whenever the caller needs
    /// the guarantee that Excel is really gone, or that the worker process
    /// itself keeps running (and thus stays visible to the supervisor's
    /// deadline tracking) until it is. See the class-level remarks.</summary>
    public void CloseAndWait()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;

        try
        {
            _workbook?.Close(false);
        }
        catch
        {
            // Best-effort; the supervisor's Job Object is the real safety net
            // if this throws.
        }

        ReleaseComObject(ref _workbook);

        try
        {
            _app?.Quit();
        }
        catch
        {
            // ditto
        }

        ReleaseComObject(ref _app);

        // Double-collect: the first pass finds RCWs with no remaining
        // references and queues their finalizers; WaitForPendingFinalizers
        // blocks until those run; the second pass sweeps the now-finalized
        // objects the first pass could only detect, not yet reclaim. A
        // single Collect()+WaitForPendingFinalizers() (the prior code here)
        // is a well-documented half-measure for exactly this reason.
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();

        if (_excelProcessId is int pid)
        {
            WaitForExcelProcessExitIndefinitely(pid);
        }
    }

    private static void WaitForExcelProcessExitIndefinitely(int pid)
    {
        while (true)
        {
            try
            {
                using var process = Process.GetProcessById(pid);
                if (process.HasExited)
                {
                    return;
                }
            }
            catch (ArgumentException)
            {
                // Process already gone.
                return;
            }

            MessagePump.PumpingDelay(TimeSpan.FromMilliseconds(300));
        }
    }

    /// <summary>IDisposable fallback for exception paths that never reach an
    /// explicit CloseAndWait() call. Best-effort only: does not wait for the
    /// Excel process to exit, so callers on the normal success path should
    /// call CloseAndWait() explicitly instead of relying on this.</summary>
    public void Dispose()
    {
        if (_disposed)
        {
            return;
        }

        _disposed = true;

        try
        {
            _workbook?.Close(false);
        }
        catch
        {
            // best-effort
        }

        ReleaseComObject(ref _workbook);

        try
        {
            _app?.Quit();
        }
        catch
        {
            // best-effort
        }

        ReleaseComObject(ref _app);

        // Double-collect: the first pass finds RCWs with no remaining
        // references and queues their finalizers; WaitForPendingFinalizers
        // blocks until those run; the second pass sweeps the now-finalized
        // objects the first pass could only detect, not yet reclaim. A
        // single Collect()+WaitForPendingFinalizers() (the prior code here)
        // is a well-documented half-measure for exactly this reason.
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();
    }

    private static void ReleaseComObject(ref dynamic? comObject)
    {
        if (comObject is null)
        {
            return;
        }

        try
        {
            if (Marshal.IsComObject(comObject))
            {
                Marshal.ReleaseComObject(comObject);
            }
        }
        catch
        {
            // best-effort
        }

        comObject = null;
    }
}
