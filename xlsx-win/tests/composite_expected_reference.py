"""Independent native-Excel reference update for composite Pivot oracles."""

from __future__ import annotations

import gc
import shutil
from pathlib import Path

from certification.excel_safety import preflight_or_raise


def _wait_for_exact_pid(pid: int) -> None:
    import psutil

    try:
        process = psutil.Process(pid)
        try:
            process.wait(timeout=30)
        except psutil.TimeoutExpired:
            process.kill()
            process.wait(timeout=10)
    except psutil.NoSuchProcess:
        pass


def build_expected_from_seed(
    seed: Path,
    output: Path,
    new_row: list[object | None],
    calculated_formulas: dict[int, str],
) -> list[dict]:
    """Append by a direct reference procedure, independent of candidate code."""

    import pythoncom
    import win32com.client
    import win32process

    shutil.copy2(seed, output)
    preflight_or_raise()
    pythoncom.CoInitialize()
    app = None
    workbook = None
    pid = 0
    reports: list[dict] = []
    data = table = cache = worksheets = sheet = pivots = pivot = None
    try:
        app = win32com.client.DispatchEx("Excel.Application")
        app.Visible = False
        app.DisplayAlerts = False
        pid = int(win32process.GetWindowThreadProcessId(int(app.Hwnd))[1])
        workbook = app.Workbooks.Open(str(output), UpdateLinks=0, ReadOnly=False)
        data = workbook.Worksheets("Data")
        table = data.ListObjects("Data")
        final_row = 3 + int(table.ListRows.Count) + 1
        data.Range(data.Cells(final_row, 2), data.Cells(final_row, 16)).Value = (tuple(new_row),)
        table.Resize(data.Range(data.Cells(3, 2), data.Cells(final_row, 16)))
        for index, formula in calculated_formulas.items():
            table.ListColumns(index + 1).DataBodyRange.FormulaR1C1 = formula

        app.CalculateFullRebuild()
        cache = workbook.PivotCaches().Item(1)
        cache.Refresh()
        worksheets = workbook.Worksheets
        for sheet_index in range(1, int(worksheets.Count) + 1):
            sheet = worksheets.Item(sheet_index)
            pivots = sheet.PivotTables()
            for pivot_index in range(1, int(pivots.Count) + 1):
                pivot = pivots.Item(pivot_index)
                pivot.Update()
                if not pivot.RefreshTable():
                    raise RuntimeError("Reference PivotTable.RefreshTable returned false.")
                reports.append(
                    {
                        "sheet": str(sheet.Name),
                        "name": str(pivot.Name),
                        "range": str(pivot.TableRange2.Address).replace("$", ""),
                    }
                )

        workbook.Save()
        pivot = pivots = sheet = worksheets = cache = table = data = None
        gc.collect()
        workbook.Close(False)
        workbook = None
        gc.collect()
        app.Quit()
    finally:
        pivot = pivots = sheet = worksheets = cache = table = data = None
        workbook = None
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        app = None
        gc.collect()
        gc.collect()
        pythoncom.CoUninitialize()
        if pid:
            _wait_for_exact_pid(pid)
    return sorted(reports, key=lambda report: (report["sheet"], report["name"]))
