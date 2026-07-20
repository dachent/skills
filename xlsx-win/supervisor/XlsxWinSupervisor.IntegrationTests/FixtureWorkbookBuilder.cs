using System.Diagnostics;
using System.Runtime.InteropServices;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Builds throwaway workbooks for integration tests via Excel COM itself
/// (Workbooks.Add() then SaveAs), inside the test's own temp directory --
/// never depending on an external fixture file. Uses its own short-lived
/// Excel.Application instance (late-bound dynamic COM, same technique as the
/// worker), separate from whatever the test-under-test later launches via
/// the supervisor, and waits for that instance's process to fully exit
/// before returning so the "is Excel already running" precondition still
/// holds for the rest of the test.
/// </summary>
internal static class FixtureWorkbookBuilder
{
    /// <summary>A trivial single-sheet workbook: A1 = 2, A2 = "=A1*2". Used
    /// for the happy-path open/recalc/save_as cycle and the dialog-prevention
    /// readback test.</summary>
    public static void CreateSimpleWorkbook(string path)
    {
        RunWithOwnExcelInstance((app, workbook) =>
        {
            dynamic sheet = workbook.Worksheets[1];
            sheet.Range["A1"].Value2 = 2;
            sheet.Range["A2"].Formula = "=A1*2";
            workbook.SaveAs(path);
        });
    }

    /// <summary>A workbook with one real WorkbookConnection (an OLEDB
    /// connection backed by a Power Query literal-list query, loaded into a
    /// worksheet table) that the refresh step must enumerate and refresh
    /// individually. No external/live data source is involved -- the query's
    /// source is a literal list, per the increment's reduced scope.</summary>
    public static void CreateWorkbookWithConnection(string path, string queryName = "TestQuery")
    {
        RunWithOwnExcelInstance((app, workbook) =>
        {
            workbook.Queries.Add(queryName, "let Source = {1, 2, 3} in Source");

            var connectionName = $"Query - {queryName}";
            var connectionString =
                $"OLEDB;Provider=Microsoft.Mashup.OleDb.1;Data Source=$Workbook$;Location={queryName};Extended Properties=\"\"";
            var commandText = $"SELECT * FROM [{queryName}]";

            dynamic connection = workbook.Connections.Add2(
                connectionName,
                $"Connection to the '{queryName}' query in the workbook.",
                connectionString,
                commandText,
                2,     // lCmdtype: xlCmdSql
                false, // CreateModelConnection
                false); // ImportRelationships

            dynamic sheet = workbook.Worksheets[1];
            dynamic destination = sheet.Range["A1"];

            // SourceType 0 = xlSrcExternal; Source is the connection object
            // itself (not its name) for a query-backed table load.
            workbook.Worksheets[1].ListObjects.Add(0, connection, true, 1, destination);

            workbook.SaveAs(path);
        });
    }

    /// <summary>A Table with one calculated column, one linked PivotCache,
    /// one PivotTable, and a staged row immediately below the current Table.
    /// The composite native step must resize, fill, calculate, refresh, save,
    /// and fresh-reopen this package without touching any external source.</summary>
    public static void CreateCompositeTablePivotWorkbook(string path)
    {
        RunWithOwnExcelInstance((app, workbook) =>
        {
            dynamic data = workbook.Worksheets[1];
            data.Name = "Data";
            object[,] values =
            {
                { "Name", "Calc", "Value" },
                { "alpha", null!, 1d },
                { "beta", null!, 2d },
            };
            data.Range["B3:D5"].Value2 = values;
            dynamic table = data.ListObjects.Add(1, data.Range["B3:D5"], Type.Missing, 1);
            table.Name = "Data";
            table.ListColumns["Calc"].DataBodyRange.FormulaR1C1 = "=RC[1]*2";

            // Candidate-A staging shape: writable values are present in the
            // future row, while the calculated cell remains empty and the
            // ListObject still owns only the original two body rows.
            data.Range["B6"].Value2 = "gamma";
            data.Range["D6"].Value2 = 3d;

            dynamic pivotSheet = workbook.Worksheets.Add();
            pivotSheet.Name = "Pivot";
            dynamic cache = workbook.PivotCaches().Create(1, "Data", 6);
            dynamic pivot = cache.CreatePivotTable(pivotSheet.Range["A3"], "Pivot1");
            pivot.PivotFields("Name").Orientation = 1;
            pivot.AddDataField(pivot.PivotFields("Value"), "Sum of Value", -4157);
            workbook.SaveAs(path);
        });
    }

    private static void RunWithOwnExcelInstance(Action<dynamic, dynamic> useWorkbook)
    {
        var excelType = Type.GetTypeFromProgID("Excel.Application")
            ?? throw new InvalidOperationException("The 'Excel.Application' ProgID is not registered on this machine.");

        dynamic? app = Activator.CreateInstance(excelType)
            ?? throw new InvalidOperationException("Activator.CreateInstance(Excel.Application) returned null.");
        dynamic? workbook = null;
        var pid = 0;

        try
        {
            app.Visible = false;
            app.DisplayAlerts = false;

            var hwnd = new IntPtr((int)app.Hwnd);
            _ = NativeMethodsForFixtures.GetWindowThreadProcessId(hwnd, out var rawPid);
            pid = unchecked((int)rawPid);

            workbook = app.Workbooks.Add();
            useWorkbook(app, workbook);

            workbook.Close(false);
        }
        finally
        {
            ReleaseIfComObject(ref workbook);

            try
            {
                app?.Quit();
            }
            catch
            {
                // best-effort
            }

            ReleaseIfComObject(ref app);

            GC.Collect();
            GC.WaitForPendingFinalizers();

            if (pid != 0)
            {
                // Real verification on this machine found EXCEL.EXE can take
                // anywhere from seconds to several minutes to actually exit
                // after Quit() returns, for reasons unrelated to this
                // fixture's own content (see README.md, "Known limitation:
                // connection-refresh shutdown latency"). This is test-fixture
                // setup, not the code under test, so once the bounded wait
                // elapses we force-terminate this exact PID -- the one this
                // method itself just launched -- rather than let it linger
                // into the actual test and trip the "Excel already running"
                // pre-flight gate or the "no survivor" post-test check for
                // reasons that have nothing to do with what's being tested.
                WaitForProcessExitOrKill(pid, TimeSpan.FromSeconds(30));
            }
        }
    }

    private static void ReleaseIfComObject(ref dynamic? comObject)
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

    private static void WaitForProcessExitOrKill(int pid, TimeSpan timeout)
    {
        var deadline = DateTime.UtcNow + timeout;
        while (DateTime.UtcNow < deadline)
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

            Thread.Sleep(200);
        }

        // Timeout elapsed and the process (this exact PID, captured at this
        // method's own launch) is still around: force it, the same way the
        // supervisor's Job Object would in production. This is fixture
        // cleanup for a process this test code itself created, not a
        // production by-name process kill.
        try
        {
            using var process = Process.GetProcessById(pid);
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch (ArgumentException)
        {
            // Already gone.
        }
    }
}

internal static partial class NativeMethodsForFixtures
{
    [System.Runtime.InteropServices.LibraryImport("user32.dll")]
    internal static partial uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
}
