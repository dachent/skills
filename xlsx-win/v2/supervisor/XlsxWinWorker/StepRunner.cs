using System.Runtime.InteropServices;
using XlsxWinContracts;

namespace XlsxWinWorker;

/// <summary>
/// Executes one job step against an already-started ExcelSession, emitting a
/// phase-transition WorkerEvent (using JobStates names) before doing the
/// work, and returning a StepResult (result.schema.json shape) either way.
/// </summary>
internal sealed class StepRunner
{
    private readonly ExcelSession _session;
    private readonly EventWriter _events;
    private readonly string _runId;
    private readonly JobTimeouts _timeouts;

    public StepRunner(ExcelSession session, EventWriter events, string runId, JobTimeouts timeouts)
    {
        _session = session;
        _events = events;
        _runId = runId;
        _timeouts = timeouts;
    }

    public StepResult Run(int index, JobStep step)
    {
        return step switch
        {
            OpenStep s => RunOpen(index, s),
            RefreshStep s => RunRefresh(index, s),
            RecalcStep s => RunRecalc(index, s),
            SaveAsStep s => RunSaveAs(index, s),
            RunApprovedMacroStep s => RunMacro(index, s),
            _ => Fail(index, step.GetType().Name, "UNKNOWN_STEP_TYPE", $"Unsupported step type: {step.GetType().Name}"),
        };
    }

    private void Emit(string phase, string? message = null, int? excelPid = null) =>
        _events.Emit(new WorkerEvent { RunId = _runId, Phase = phase, Message = message, ExcelPid = excelPid });

    private StepResult RunOpen(int index, OpenStep step)
    {
        Emit("OPENING_WORKBOOK", $"Opening '{step.WorkbookPath}'.");
        try
        {
            _session.Open(step.WorkbookPath, step.ReadOnly ?? false, step.UpdateLinks ?? false);
            return Succeed(index, "open", $"Opened '{step.WorkbookPath}'.");
        }
        catch (Exception ex)
        {
            return Fail(index, "open", "OPEN_WORKBOOK_FAILED", ex.Message);
        }
    }

    private StepResult RunRefresh(int index, RefreshStep step)
    {
        Emit("REFRESHING_CONNECTIONS", "Enumerating workbook connections.");

        var workbook = _session.Workbook;
        if (workbook is null)
        {
            return Fail(index, "refresh", "NO_WORKBOOK_OPEN", "No workbook is open to refresh.");
        }

        var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(_timeouts.RefreshTotalSeconds);
        var wanted = step.Connections.All ? null : new HashSet<string>(step.Connections.Names, StringComparer.OrdinalIgnoreCase);

        var failures = new List<string>();
        var refreshedNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        dynamic? connections = null;
        try
        {
            try
            {
                connections = workbook.Connections;
            }
            catch (Exception ex)
            {
                // A transient RPC/disconnected COM error accessing the
                // Connections property itself must not propagate out of
                // StepRunner.Run: unlike every other step handler in this file,
                // this used to be unguarded, so a COM hiccup here would crash the
                // worker process outright with no FAILED step recorded and no
                // final result.json written for this run.
                return Fail(index, "refresh", "REFRESH_FAILED", $"Failed to access workbook connections: {ex.Message}");
            }

            try
            {
                foreach (dynamic connection in connections)
                {
                    try
                    {
                        string connectionName;
                        try
                        {
                            connectionName = connection.Name;
                        }
                        catch (Exception ex)
                        {
                            failures.Add($"<unknown connection>: failed to read connection name: {ex.Message}");
                            continue;
                        }

                        try
                        {
                            if (wanted is not null && !wanted.Contains(connectionName))
                            {
                                continue;
                            }

                            RefreshOneConnection(connection, deadline);
                            refreshedNames.Add(connectionName);
                        }
                        catch (Exception ex)
                        {
                            failures.Add($"{connectionName}: {ex.Message}");
                        }
                    }
                    finally
                    {
                        // Release this Connection RCW before the enumerator
                        // advances. Confirmed root cause (not a guess): a
                        // genuine Power-Query/OLEDB-backed connection object
                        // left unreleased here keeps EXCEL.EXE alive for
                        // minutes after Application.Quit(), even though the
                        // refresh itself already completed in seconds -- see
                        // README.md's power_query_minimal finding. This is
                        // the standard COM-interop rule (every intermediate
                        // object obtained via property/collection access
                        // needs an explicit Marshal.ReleaseComObject; a
                        // variable going out of scope is not enough, since
                        // Excel won't exit until every outstanding COM
                        // reference is released, and the .NET GC alone can
                        // take multiple collection cycles to get there).
                        ReleaseComObject(connection);
                    }
                }
            }
            catch (Exception ex)
            {
                // The foreach enumerator itself (MoveNext/Current on the COM
                // collection) can throw independently of any per-connection
                // work. Converting this to a REFRESH_FAILED step result -- rather
                // than letting it crash the worker process -- is exactly the
                // robustness this supervisor exists to add.
                return Fail(index, "refresh", "REFRESH_FAILED", $"Failed while enumerating workbook connections: {ex.Message}");
            }
        }
        finally
        {
            if (connections is not null)
            {
                ReleaseComObject(connections);
            }
        }

        if (wanted is not null)
        {
            foreach (var missingName in wanted.Where(name => !refreshedNames.Contains(name)))
            {
                if (!failures.Any(f => f.StartsWith(missingName + ":", StringComparison.OrdinalIgnoreCase)))
                {
                    failures.Add($"{missingName}: connection not found in workbook.");
                }
            }
        }

        if (failures.Count > 0)
        {
            return Fail(index, "refresh", "REFRESH_FAILED", string.Join("; ", failures));
        }

        return Succeed(index, "refresh", $"Refreshed {refreshedNames.Count} connection(s) individually (no RefreshAll).");
    }

    private static void RefreshOneConnection(dynamic connection, DateTime deadline)
    {
        // Prefer synchronous refresh where the connection type honors
        // BackgroundQuery; poll .Refreshing afterwards regardless, since some
        // connection types ignore BackgroundQuery entirely.
        TrySetBackgroundQueryOff(connection);

        connection.Refresh();

        while (DateTime.UtcNow < deadline)
        {
            if (!IsStillRefreshing(connection))
            {
                return;
            }

            MessagePump.PumpingDelay(TimeSpan.FromMilliseconds(200));
        }

        throw new TimeoutException($"Connection '{connection.Name}' did not finish refreshing within the refresh deadline.");
    }

    private static void TrySetBackgroundQueryOff(dynamic connection)
    {
        dynamic? oledb = null;
        try
        {
            oledb = connection.OLEDBConnection;
            if (oledb is not null)
            {
                oledb.BackgroundQuery = false;
            }
        }
        catch
        {
            // Not every connection exposes OLEDBConnection; ignore.
        }
        finally
        {
            if (oledb is not null)
            {
                ReleaseComObject(oledb);
            }
        }

        dynamic? odbc = null;
        try
        {
            odbc = connection.ODBCConnection;
            if (odbc is not null)
            {
                odbc.BackgroundQuery = false;
            }
        }
        catch
        {
            // Not every connection exposes ODBCConnection; ignore.
        }
        finally
        {
            if (odbc is not null)
            {
                ReleaseComObject(odbc);
            }
        }
    }

    private static bool IsStillRefreshing(dynamic connection)
    {
        dynamic? oledb = null;
        try
        {
            oledb = connection.OLEDBConnection;
            if (oledb is not null && (bool)oledb.Refreshing)
            {
                return true;
            }
        }
        catch
        {
            // Connection type does not expose OLEDBConnection at all.
        }
        finally
        {
            if (oledb is not null)
            {
                ReleaseComObject(oledb);
            }
        }

        dynamic? odbc = null;
        try
        {
            odbc = connection.ODBCConnection;
            if (odbc is not null && (bool)odbc.Refreshing)
            {
                return true;
            }
        }
        catch
        {
            // Connection type does not expose ODBCConnection at all.
        }
        finally
        {
            if (odbc is not null)
            {
                ReleaseComObject(odbc);
            }
        }

        // Worksheet/text/model/etc. connection types don't expose a Refreshing
        // flag at all -- treat Refresh() having returned as completion.
        return false;
    }

    /// <summary>Releases one COM RCW, best-effort. Every intermediate COM
    /// object this file obtains via property/collection access on a
    /// Workbook/Connections/Connection (never just the top-level
    /// Workbook/Application ExcelSession.cs already handles) needs this --
    /// letting a local `dynamic` variable go out of scope is not enough;
    /// Excel will not actually exit until every outstanding COM reference is
    /// released, and relying on the .NET GC alone to get there can take
    /// multiple collection cycles. See RunRefresh's finally blocks for the
    /// confirmed real-world consequence of skipping this.</summary>
    private static void ReleaseComObject(object? comObject)
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
            // best-effort, mirroring ExcelSession.cs's own ReleaseComObject.
        }
    }

    private StepResult RunRecalc(int index, RecalcStep step)
    {
        Emit("CALCULATING", $"mode={step.Mode}");

        var app = _session.App;
        var timeoutSeconds = step.TimeoutSeconds ?? _timeouts.CalculationSeconds;
        var deadline = DateTime.UtcNow + TimeSpan.FromSeconds(timeoutSeconds);

        try
        {
            if (string.Equals(step.Mode, "normal", StringComparison.OrdinalIgnoreCase))
            {
                app.Calculate();
            }
            else
            {
                app.CalculateFullRebuild();
            }

            while ((int)app.CalculationState != ExcelConstants.XlDone)
            {
                if (DateTime.UtcNow >= deadline)
                {
                    return Fail(index, "recalc", "CALCULATION_TIMEOUT", $"Calculation did not reach xlDone within {timeoutSeconds}s.");
                }

                MessagePump.PumpingDelay(TimeSpan.FromMilliseconds(200));
            }

            return Succeed(index, "recalc", "Calculation reached xlDone.");
        }
        catch (Exception ex)
        {
            return Fail(index, "recalc", "CALCULATION_FAILED", ex.Message);
        }
    }

    private StepResult RunSaveAs(int index, SaveAsStep step)
    {
        Emit("SAVING", $"Saving to '{step.OutputPath}'.");

        if (File.Exists(step.OutputPath) && step.Overwrite != true)
        {
            return Fail(index, "save_as", "OUTPUT_EXISTS",
                $"'{step.OutputPath}' already exists and overwrite was not explicitly requested.");
        }

        try
        {
            _session.SaveAs(step.OutputPath);
            return Succeed(index, "save_as", $"Saved to '{step.OutputPath}'.");
        }
        catch (Exception ex)
        {
            return Fail(index, "save_as", "SAVE_FAILED", ex.Message);
        }
    }

    private StepResult RunMacro(int index, RunApprovedMacroStep step)
    {
        Emit("RUNNING_APPROVED_MACRO", $"macro_name={step.MacroName}");

        // Explicitly deferred to a later increment -- see README.md
        // "Explicitly deferred". This is a deliberate, visible failure, not a
        // silent no-op: re-enabling AutomationSecurity around a macro call and
        // allowlist-checking the macro name is real work this increment does
        // not implement.
        return Fail(
            index,
            "run_approved_macro",
            "MACRO_EXECUTION_DEFERRED",
            $"run_approved_macro ('{step.MacroName}') is not implemented in this increment. " +
            "See supervisor/README.md, 'Explicitly deferred to a later increment'.");
    }

    private static StepResult Succeed(int index, string type, string message) => new()
    {
        StepIndex = index,
        Type = type,
        Status = "succeeded",
        Message = message,
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
