using System.Diagnostics;

namespace XlsxWinWorker;

internal sealed class ExcelSession : IDisposable
{
    private dynamic? _app;
    private dynamic? _workbook;
    private int? _excelProcessId;
    private bool _disposed;

    public ExcelSession(ComGateway? gateway = null)
    {
        Gateway = gateway ?? new ComGateway();
    }

    public ComGateway Gateway { get; }
    public dynamic App => _app ?? throw new InvalidOperationException("Excel has not been started.");
    public dynamic? Workbook => _workbook;
    public int? ExcelProcessId => _excelProcessId;

    public int Start()
    {
        var excelType = Type.GetTypeFromProgID("Excel.Application")
            ?? throw new InvalidOperationException("The 'Excel.Application' ProgID is not registered. Is Excel installed?");
        _app = Gateway.Acquire("STARTING_EXCEL", "CoCreateInstance", () =>
            Activator.CreateInstance(excelType)
            ?? throw new InvalidOperationException("Activator.CreateInstance(Excel.Application) returned null."));
        Gateway.Invoke("STARTING_EXCEL", "Visible=false", () => _app.Visible = false);
        Gateway.Invoke("STARTING_EXCEL", "DisplayAlerts=false", () => _app.DisplayAlerts = false);
        Gateway.Invoke("STARTING_EXCEL", "AskToUpdateLinks=false", () => _app.AskToUpdateLinks = false);
        Gateway.Invoke("STARTING_EXCEL", "AutomationSecurity=ForceDisable", () =>
            _app.AutomationSecurity = ExcelConstants.MsoAutomationSecurityForceDisable);
        _excelProcessId = CaptureExcelProcessId();
        return _excelProcessId.Value;
    }

    public (bool DisplayAlerts, bool AskToUpdateLinks, int AutomationSecurity) ReadDialogPreventionState() =>
        Gateway.Invoke("STARTING_EXCEL", "dialog_prevention_readback", () =>
            ((bool)App.DisplayAlerts, (bool)App.AskToUpdateLinks, (int)App.AutomationSecurity));

    public int CaptureExcelProcessId()
    {
        var hwndValue = Gateway.Invoke("STARTING_EXCEL", "Application.Hwnd", () => (int)App.Hwnd);
        NativeMethods.GetWindowThreadProcessId(new IntPtr(hwndValue), out var pid);
        if (pid == 0) throw new InvalidOperationException("Application.Hwnd did not resolve to an Excel PID.");
        return unchecked((int)pid);
    }

    public dynamic Open(string workbookPath, bool readOnly, bool updateLinks)
    {
        var updateLinksValue = updateLinks ? ExcelConstants.UpdateLinksAlways : ExcelConstants.UpdateLinksNever;
        dynamic? workbooks = null;
        try
        {
            workbooks = Gateway.Acquire("OPENING_WORKBOOK", "Application.Workbooks", () => App.Workbooks);
            _workbook = Gateway.Acquire("OPENING_WORKBOOK", "Workbooks.Open", () =>
                workbooks.Open(workbookPath, updateLinksValue, readOnly));
            return _workbook;
        }
        finally
        {
            Gateway.Release(workbooks);
        }
    }

    public void SaveAs(string outputPath)
    {
        var workbook = _workbook ?? throw new InvalidOperationException("No workbook is open.");
        Gateway.Invoke("SAVING", "Workbook.SaveAs", () => workbook.SaveAs(outputPath));
    }

    public void CloseWorkbook(bool saveChanges = false)
    {
        if (_workbook is null || Gateway.IsPoisoned) return;
        var workbook = _workbook;
        Gateway.Invoke("REOPENING", "Workbook.Close", () => workbook.Close(saveChanges));
        Gateway.Release(workbook);
        _workbook = null;
    }

    public void CloseAndWait()
    {
        if (_disposed) return;
        _disposed = true;
        if (Gateway.IsPoisoned)
        {
            // Keep root RCWs alive and issue no close/quit/release/GC calls.
            // The supervisor owns Job Object termination.
            return;
        }
        try { CloseWorkbook(false); } catch { }
        var app = _app;
        if (app is not null)
        {
            try { Gateway.Invoke("CLOSING", "Application.Quit", () => app.Quit()); } catch { }
            Gateway.Release(app);
            _app = null;
        }
        GC.Collect();
        GC.WaitForPendingFinalizers();
        GC.Collect();
        if (_excelProcessId is int pid) WaitForExcelProcessExitIndefinitely(pid);
    }

    private static void WaitForExcelProcessExitIndefinitely(int pid)
    {
        while (true)
        {
            try
            {
                using var process = Process.GetProcessById(pid);
                if (process.HasExited) return;
            }
            catch (ArgumentException)
            {
                return;
            }
            MessagePump.PumpingDelay(TimeSpan.FromMilliseconds(300));
        }
    }

    public void Dispose()
    {
        if (_disposed) return;
        if (Gateway.IsPoisoned)
        {
            _disposed = true;
            return;
        }
        CloseAndWait();
    }
}
