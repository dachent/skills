using System.Runtime.InteropServices;
using XlsxWinContracts;

namespace XlsxWinWorker;

/// <summary>
/// Native Excel half of the v2.1 transaction. Bulk constants have already
/// been streamed into an allowlisted intermediate package. This class owns
/// only Table resize, calculated-column fill, calculation, linked Pivot
/// refresh/redraw, save, close, fresh reopen, and native verification.
/// </summary>
internal sealed class CompositeNativeRunner
{
    private const int XlDone = 0;
    private const int XlSrcRange = 1;
    private const int XlDescending = 2;
    private const int XlCalculationManual = -4135;
    private const int XlCalculationAutomatic = -4105;

    private readonly ExcelSession _session;
    private readonly EventWriter _events;
    private readonly string _runId;
    private readonly JobTimeouts _timeouts;
    private ComGateway Gateway => _session.Gateway;

    public CompositeNativeRunner(ExcelSession session, EventWriter events, string runId, JobTimeouts timeouts)
    {
        _session = session;
        _events = events;
        _runId = runId;
        _timeouts = timeouts;
    }

    public StepResult Run(int index, CompositeTableStep step)
    {
        try
        {
            Emit("COMPOSITE_PREFLIGHT", $"Native preflight for {step.Table.Sheet}!{step.Table.Name}.");
            dynamic? calculationBootstrap = null;
            try
            {
                calculationBootstrap = OpenCalculationBootstrap();
                _session.Open(step.WorkbookPath, readOnly: false, updateLinks: false);
            }
            finally
            {
                CloseCalculationBootstrap(calculationBootstrap);
            }
            Emit("COMPOSITE_PREFLIGHT", "Workbook opened in manual calculation mode; inspecting native Table state.");
            var formulas = InspectTable(step, requireExistingRows: false, captureFormulas: true);

            Emit("APPLYING_EDITS", $"Resizing Table to {step.Table.FinalBodyRows} body rows.");
            ResizeAndFillCalculatedColumns(step, formulas);

            Emit("CALCULATING", "Running CalculateFullRebuild and waiting for xlDone.");
            Gateway.Invoke("CALCULATING", "Application.Calculation=Automatic", () =>
                _session.App.Calculation = XlCalculationAutomatic);
            Calculate();

            Emit("REFRESHING_PIVOTS", "Refreshing the exact declared cache/report topology.");
            RefreshPivots(step);

            if (File.Exists(step.OutputPath))
            {
                return Fail(index, step.OperationType, "OUTPUT_EXISTS", "Composite staged output already exists; refusing to overwrite it.");
            }
            Emit("SAVING", $"Saving verified native work to '{step.OutputPath}'.");
            _session.SaveAs(step.OutputPath);

            Emit("REOPENING", "Closing and freshly reopening the saved output.");
            _session.CloseWorkbook(false);
            _session.Open(step.OutputPath, readOnly: false, updateLinks: false);

            Emit("VALIDATING", "Rechecking Table, formulas, sort/filter state, and Pivot topology after reopen.");
            InspectTable(step, requireExistingRows: false, captureFormulas: false);
            VerifyPivots(step);
            _session.CloseWorkbook(false);

            return Succeed(index, step.OperationType,
                $"Native transaction completed; tracked_owned_rcw_leases={Gateway.TrackedOwnedRcwLeases}, " +
                $"high_water={Gateway.TrackedOwnedRcwHighWater}.");
        }
        catch (ExcelSessionPoisonedException ex)
        {
            Emit("FAILED", $"poison:{ex.Evidence.Code};origin={ex.Evidence.Origin};operation={ex.Evidence.Operation}");
            return new StepResult
            {
                StepIndex = index,
                Type = step.OperationType,
                Status = "failed",
                Message = ex.Message,
                Error = new ErrorDetail
                {
                    Code = ex.Evidence.Code,
                    Message = ex.Evidence.Message,
                    Details = new Dictionary<string, object?>
                    {
                        ["origin"] = ex.Evidence.Origin,
                        ["phase"] = ex.Evidence.Phase,
                        ["operation"] = ex.Evidence.Operation,
                        ["hresult"] = $"0x{unchecked((uint)ex.Evidence.HResult):X8}",
                        ["zero_further_excel_calls_latched"] = true,
                    },
                },
            };
        }
        catch (Exception ex)
        {
            return Fail(index, step.OperationType, "COMPOSITE_NATIVE_FAILED", ex.Message);
        }
    }

    private dynamic OpenCalculationBootstrap()
    {
        dynamic? workbooks = null;
        dynamic? bootstrap = null;
        try
        {
            workbooks = Gateway.Acquire("COMPOSITE_PREFLIGHT", "Application.Workbooks", () => _session.App.Workbooks);
            bootstrap = Gateway.Acquire("COMPOSITE_PREFLIGHT", "Workbooks.Add", () => workbooks.Add());
            Gateway.Invoke("COMPOSITE_PREFLIGHT", "Application.Calculation=Manual", () =>
                _session.App.Calculation = XlCalculationManual);
            return bootstrap;
        }
        catch
        {
            Gateway.Release(bootstrap);
            throw;
        }
        finally
        {
            Gateway.Release(workbooks);
        }
    }

    private void CloseCalculationBootstrap(dynamic? bootstrap)
    {
        if (bootstrap is null) return;
        try
        {
            Gateway.Invoke("COMPOSITE_PREFLIGHT", "BootstrapWorkbook.Close", () => bootstrap.Close(false));
        }
        finally
        {
            Gateway.Release(bootstrap);
        }
    }

    private Dictionary<int, object?> InspectTable(CompositeTableStep step, bool requireExistingRows, bool captureFormulas)
    {
        dynamic? worksheets = null;
        dynamic? sheet = null;
        dynamic? tables = null;
        dynamic? table = null;
        dynamic? listRows = null;
        dynamic? listColumns = null;
        dynamic? tableRange = null;
        dynamic? sort = null;
        dynamic? sortFields = null;
        var formulas = new Dictionary<int, object?>();
        try
        {
            var workbook = _session.Workbook ?? throw new InvalidOperationException("No workbook is open.");
            worksheets = Gateway.Acquire("VALIDATING", "Workbook.Worksheets", () => workbook.Worksheets);
            sheet = Gateway.Acquire("VALIDATING", "Worksheets.Item", () => worksheets.Item(step.Table.Sheet));
            tables = Gateway.Acquire("VALIDATING", "Worksheet.ListObjects", () => sheet.ListObjects);
            table = Gateway.Acquire("VALIDATING", "ListObjects.Item", () => tables.Item(step.Table.Name));

            var sourceType = Gateway.Invoke("VALIDATING", "ListObject.SourceType", () => (int)table.SourceType);
            var totals = Gateway.Invoke("VALIDATING", "ListObject.ShowTotals", () => (bool)table.ShowTotals);
            var filterMode = Gateway.Invoke("VALIDATING", "Worksheet.FilterMode", () => (bool)sheet.FilterMode);
            if (sourceType != XlSrcRange || totals || filterMode)
                throw new InvalidOperationException("Native Table source/totals/filter state is outside the profile.");

            listRows = Gateway.Acquire("VALIDATING", "ListObject.ListRows", () => table.ListRows);
            var rowCount = Gateway.Invoke("VALIDATING", "ListRows.Count", () => (int)listRows.Count);
            var expectedRows = requireExistingRows ? step.Table.ExistingBodyRows : step.Table.FinalBodyRows;
            if (rowCount != expectedRows)
                throw new InvalidOperationException($"Native Table row count {rowCount} != expected {expectedRows}.");

            listColumns = Gateway.Acquire("VALIDATING", "ListObject.ListColumns", () => table.ListColumns);
            var columnCount = Gateway.Invoke("VALIDATING", "ListColumns.Count", () => (int)listColumns.Count);
            if (columnCount != step.Table.ColumnCount) throw new InvalidOperationException("Native Table column count changed.");
            for (var index = 1; index <= columnCount; index++)
            {
                dynamic? column = null;
                dynamic? body = null;
                dynamic? cells = null;
                dynamic? firstCell = null;
                dynamic? lastCell = null;
                try
                {
                    column = Gateway.Acquire("VALIDATING", "ListColumns.Item", () => listColumns.Item(index));
                    var name = Gateway.Invoke("VALIDATING", "ListColumn.Name", () => (string)column.Name);
                    var spec = step.Table.Columns[index - 1];
                    if (!string.Equals(name, spec.Name, StringComparison.Ordinal))
                        throw new InvalidOperationException($"Table column {index} is '{name}', expected '{spec.Name}'.");
                    if (string.Equals(spec.Role, "calculated", StringComparison.Ordinal))
                    {
                        body = Gateway.Acquire("VALIDATING", "ListColumn.DataBodyRange", () => column.DataBodyRange);
                        cells = Gateway.Acquire("VALIDATING", "DataBodyRange.Cells", () => body.Cells);
                        firstCell = Gateway.Acquire("VALIDATING", "DataBodyRange.Cells.Item(first)", () => cells.Item(1, 1));
                        var formulaBoundaryRow = captureFormulas ? step.Table.ExistingBodyRows : rowCount;
                        lastCell = Gateway.Acquire("VALIDATING", "DataBodyRange.Cells.Item(last)", () => cells.Item(formulaBoundaryRow, 1));
                        var firstHasFormula = Gateway.Invoke("VALIDATING", "FirstCell.HasFormula", () => (bool)firstCell.HasFormula);
                        var lastHasFormula = Gateway.Invoke("VALIDATING", "LastCell.HasFormula", () => (bool)lastCell.HasFormula);
                        if (!firstHasFormula || !lastHasFormula)
                            throw new InvalidOperationException($"Calculated column '{name}' boundary cells are not formula-backed.");
                        var firstFormula = Gateway.Invoke(
                            captureFormulas ? "COMPOSITE_PREFLIGHT" : "VALIDATING",
                            "FirstCell.FormulaR1C1",
                            () => (string)firstCell.FormulaR1C1);
                        var lastFormula = Gateway.Invoke("VALIDATING", "LastCell.FormulaR1C1", () => (string)lastCell.FormulaR1C1);
                        if (!string.Equals(firstFormula, lastFormula, StringComparison.Ordinal))
                            throw new InvalidOperationException($"Calculated column '{name}' boundary formulas differ.");
                        if (captureFormulas)
                            formulas[index] = firstFormula;
                    }
                }
                finally
                {
                    Gateway.Release(lastCell);
                    Gateway.Release(firstCell);
                    Gateway.Release(cells);
                    Gateway.Release(body);
                    Gateway.Release(column);
                }
            }

            sort = Gateway.Acquire("VALIDATING", "ListObject.Sort", () => table.Sort);
            sortFields = Gateway.Acquire("VALIDATING", "Sort.SortFields", () => sort.SortFields);
            var sortCount = Gateway.Invoke("VALIDATING", "SortFields.Count", () => (int)sortFields.Count);
            if (step.Table.SavedSort is null)
            {
                if (sortCount != 0) throw new InvalidOperationException("A saved sort descriptor exists but the profile requires none.");
            }
            else
            {
                if (sortCount != 1) throw new InvalidOperationException("The saved sort descriptor was not preserved exactly.");
                dynamic? field = null;
                dynamic? key = null;
                try
                {
                    field = Gateway.Acquire("VALIDATING", "SortFields.Item", () => sortFields.Item(1));
                    var order = Gateway.Invoke("VALIDATING", "SortField.Order", () => (int)field.Order);
                    key = Gateway.Acquire("VALIDATING", "SortField.Key", () => field.Key);
                    var keyColumn = Gateway.Invoke("VALIDATING", "SortField.Key.Column", () => (int)key.Column);
                    tableRange = Gateway.Acquire("VALIDATING", "ListObject.Range", () => table.Range);
                    var firstColumn = Gateway.Invoke("VALIDATING", "ListObject.Range.Column", () => (int)tableRange.Column);
                    var expectedOffset = step.Table.Columns.FindIndex(c => c.Name == step.Table.SavedSort.Column);
                    if (order != XlDescending || keyColumn != firstColumn + expectedOffset)
                        throw new InvalidOperationException("Saved sort column/direction changed.");
                }
                finally
                {
                    Gateway.Release(key);
                    Gateway.Release(field);
                }
            }
            return formulas;
        }
        finally
        {
            Gateway.Release(sortFields);
            Gateway.Release(sort);
            Gateway.Release(tableRange);
            Gateway.Release(listColumns);
            Gateway.Release(listRows);
            Gateway.Release(table);
            Gateway.Release(tables);
            Gateway.Release(sheet);
            Gateway.Release(worksheets);
        }
    }

    private void ResizeAndFillCalculatedColumns(CompositeTableStep step, Dictionary<int, object?> formulas)
    {
        dynamic? worksheets = null;
        dynamic? sheet = null;
        dynamic? tables = null;
        dynamic? table = null;
        dynamic? currentRange = null;
        dynamic? targetRange = null;
        dynamic? columns = null;
        try
        {
            var workbook = _session.Workbook ?? throw new InvalidOperationException("No workbook is open.");
            worksheets = Gateway.Acquire("APPLYING_EDITS", "Workbook.Worksheets", () => workbook.Worksheets);
            sheet = Gateway.Acquire("APPLYING_EDITS", "Worksheets.Item", () => worksheets.Item(step.Table.Sheet));
            tables = Gateway.Acquire("APPLYING_EDITS", "Worksheet.ListObjects", () => sheet.ListObjects);
            table = Gateway.Acquire("APPLYING_EDITS", "ListObjects.Item", () => tables.Item(step.Table.Name));
            currentRange = Gateway.Acquire("APPLYING_EDITS", "ListObject.Range", () => table.Range);
            var firstRow = Gateway.Invoke("APPLYING_EDITS", "Range.Row", () => (int)currentRange.Row);
            var firstColumn = Gateway.Invoke("APPLYING_EDITS", "Range.Column", () => (int)currentRange.Column);
            var finalRow = firstRow + step.Table.FinalBodyRows;
            var finalColumn = firstColumn + step.Table.ColumnCount - 1;
            var startAddress = $"{ColumnLetters(firstColumn)}{firstRow}";
            var endAddress = $"{ColumnLetters(finalColumn)}{finalRow}";
            targetRange = Gateway.Acquire("APPLYING_EDITS", "Worksheet.Range", () => sheet.Range[startAddress, endAddress]);
            Gateway.Invoke("APPLYING_EDITS", "ListObject.Resize", () => table.Resize(targetRange));

            columns = Gateway.Acquire("APPLYING_EDITS", "ListObject.ListColumns", () => table.ListColumns);
            foreach (var entry in formulas)
            {
                dynamic? column = null;
                dynamic? body = null;
                try
                {
                    column = Gateway.Acquire("APPLYING_EDITS", "ListColumns.Item", () => columns.Item(entry.Key));
                    body = Gateway.Acquire("APPLYING_EDITS", "ListColumn.DataBodyRange", () => column.DataBodyRange);
                    var formula = entry.Value;
                    Gateway.Invoke("APPLYING_EDITS", "DataBodyRange.FormulaR1C1", () => body.FormulaR1C1 = formula);
                }
                finally
                {
                    Gateway.Release(body);
                    Gateway.Release(column);
                }
            }
        }
        finally
        {
            Gateway.Release(columns);
            Gateway.Release(targetRange);
            Gateway.Release(currentRange);
            Gateway.Release(table);
            Gateway.Release(tables);
            Gateway.Release(sheet);
            Gateway.Release(worksheets);
        }
    }

    private void Calculate()
    {
        Gateway.Invoke("CALCULATING", "Application.CalculateFullRebuild", () => _session.App.CalculateFullRebuild());
        var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(_timeouts.CalculationSeconds);
        while (Gateway.Invoke("CALCULATING", "Application.CalculationState", () => (int)_session.App.CalculationState) != XlDone)
        {
            if (DateTime.UtcNow >= deadline) throw new TimeoutException("Calculation did not reach xlDone.");
            MessagePump.PumpingDelay(TimeSpan.FromMilliseconds(200));
        }
    }

    private void RefreshPivots(CompositeTableStep step)
    {
        dynamic? caches = null;
        try
        {
            var workbook = _session.Workbook ?? throw new InvalidOperationException("No workbook is open.");
            caches = Gateway.Acquire("REFRESHING_PIVOTS", "Workbook.PivotCaches", () => workbook.PivotCaches());
            var count = Gateway.Invoke("REFRESHING_PIVOTS", "PivotCaches.Count", () => (int)caches.Count);
            if (count != step.DependentPivots.CacheCount) throw new InvalidOperationException("Native Pivot cache count is outside the exact profile.");
            for (var index = 1; index <= count; index++)
            {
                dynamic? cache = null;
                try
                {
                    cache = Gateway.Acquire("REFRESHING_PIVOTS", "PivotCaches.Item", () => caches.Item(index));
                    Gateway.Invoke("REFRESHING_PIVOTS", "PivotCache.Refresh", () => cache.Refresh());
                }
                finally { Gateway.Release(cache); }
            }
        }
        finally { Gateway.Release(caches); }
        RefreshOrCountReports(step, refresh: true);
    }

    private void VerifyPivots(CompositeTableStep step) => RefreshOrCountReports(step, refresh: false);

    private void RefreshOrCountReports(CompositeTableStep step, bool refresh)
    {
        dynamic? worksheets = null;
        var reportCount = 0;
        try
        {
            var workbook = _session.Workbook ?? throw new InvalidOperationException("No workbook is open.");
            worksheets = Gateway.Acquire("REFRESHING_PIVOTS", "Workbook.Worksheets", () => workbook.Worksheets);
            var sheetCount = Gateway.Invoke("REFRESHING_PIVOTS", "Worksheets.Count", () => (int)worksheets.Count);
            for (var sheetIndex = 1; sheetIndex <= sheetCount; sheetIndex++)
            {
                dynamic? sheet = null;
                dynamic? reports = null;
                try
                {
                    sheet = Gateway.Acquire("REFRESHING_PIVOTS", "Worksheets.Item", () => worksheets.Item(sheetIndex));
                    reports = Gateway.Acquire("REFRESHING_PIVOTS", "Worksheet.PivotTables", () => sheet.PivotTables());
                    var count = Gateway.Invoke("REFRESHING_PIVOTS", "PivotTables.Count", () => (int)reports.Count);
                    reportCount += count;
                    if (!refresh) continue;
                    for (var reportIndex = 1; reportIndex <= count; reportIndex++)
                    {
                        dynamic? report = null;
                        try
                        {
                            report = Gateway.Acquire("REFRESHING_PIVOTS", "PivotTables.Item", () => reports.Item(reportIndex));
                            Gateway.Invoke("REFRESHING_PIVOTS", "PivotTable.Update", () => report.Update());
                            var refreshed = Gateway.Invoke("REFRESHING_PIVOTS", "PivotTable.RefreshTable", () => (bool)report.RefreshTable());
                            if (!refreshed) throw new InvalidOperationException("PivotTable.RefreshTable returned false.");
                        }
                        finally { Gateway.Release(report); }
                    }
                }
                finally
                {
                    Gateway.Release(reports);
                    Gateway.Release(sheet);
                }
            }
        }
        finally { Gateway.Release(worksheets); }
        if (reportCount != step.DependentPivots.ReportCount)
            throw new InvalidOperationException($"Native Pivot report count {reportCount} != expected {step.DependentPivots.ReportCount}.");
    }

    private void Emit(string phase, string message) =>
        _events.Emit(new WorkerEvent { RunId = _runId, Phase = phase, Message = message });

    private static string ColumnLetters(int number)
    {
        var result = "";
        while (number > 0)
        {
            number--;
            result = (char)('A' + number % 26) + result;
            number /= 26;
        }
        return result;
    }

    private static StepResult Succeed(int index, string type, string message) => new()
    {
        StepIndex = index, Type = type, Status = "succeeded", Message = message,
    };

    private static StepResult Fail(int index, string type, string code, string message) => new()
    {
        StepIndex = index,
        Type = type,
        Status = "failed",
        Message = message,
        Error = new ErrorDetail { Code = code, Message = message },
    };
}
