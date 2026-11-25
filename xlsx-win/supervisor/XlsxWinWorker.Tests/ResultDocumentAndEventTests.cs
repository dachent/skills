using XlsxWinContracts;

namespace XlsxWinWorker.Tests;

public class ResultDocumentAndEventTests
{
    [Fact]
    public void Ok_is_true_only_when_every_step_succeeded_and_every_invariant_passed()
    {
        var allGood = ResultDocument.Build(
            "run-1", "key-1", "SUCCEEDED",
            new List<StepResult> { new() { StepIndex = 0, Type = "open", Status = "succeeded" } },
            new List<InvariantResult> { new() { Name = "row_count", Passed = true } });

        Assert.True(allGood.Ok);

        var stepFailed = ResultDocument.Build(
            "run-2", "key-2", "FAILED",
            new List<StepResult> { new() { StepIndex = 0, Type = "open", Status = "failed" } });

        Assert.False(stepFailed.Ok);

        var invariantFailed = ResultDocument.Build(
            "run-3", "key-3", "SUCCEEDED",
            new List<StepResult> { new() { StepIndex = 0, Type = "open", Status = "succeeded" } },
            new List<InvariantResult> { new() { Name = "row_count", Passed = false } });

        Assert.False(invariantFailed.Ok);
    }

    [Fact]
    public void Skipped_step_status_prevents_ok()
    {
        var result = ResultDocument.Build(
            "run-4", "key-4", "FAILED",
            new List<StepResult>
            {
                new() { StepIndex = 0, Type = "open", Status = "failed" },
                new() { StepIndex = 1, Type = "refresh", Status = "skipped" },
            });

        Assert.False(result.Ok);
    }

    [Fact]
    public void Round_trips_through_json()
    {
        var original = ResultDocument.Build(
            "run-5", "key-5", "SUCCEEDED",
            new List<StepResult> { new() { StepIndex = 0, Type = "open", Status = "succeeded", Message = "opened" } });

        var reparsed = ResultDocument.Parse(original.ToJson());

        Assert.Equal(original.RunId, reparsed.RunId);
        Assert.Equal(original.FinalState, reparsed.FinalState);
        Assert.Equal(original.Ok, reparsed.Ok);
        Assert.Single(reparsed.Steps);
        Assert.Equal("opened", reparsed.Steps[0].Message);
    }

    [Fact]
    public void Worker_event_round_trips_and_uses_a_known_state_name()
    {
        var evt = new WorkerEvent { RunId = "run-6", Phase = "REFRESHING_CONNECTIONS", ExcelPid = 4242 };

        Assert.Contains(evt.Phase, JobStates.States);

        var line = evt.ToJsonLine();
        var reparsed = WorkerEvent.TryParse(line);

        Assert.NotNull(reparsed);
        Assert.Equal("run-6", reparsed!.RunId);
        Assert.Equal("REFRESHING_CONNECTIONS", reparsed.Phase);
        Assert.Equal(4242, reparsed.ExcelPid);
    }

    [Fact]
    public void Worker_event_row_counts_round_trip_through_json()
    {
        var evt = new WorkerEvent
        {
            RunId = "run-rows",
            Phase = "COMPOSITE_PREFLIGHT",
            RowsDone = 195935,
            RowsTotal = 463000,
        };

        var reparsed = WorkerEvent.TryParse(evt.ToJsonLine());

        Assert.NotNull(reparsed);
        Assert.Equal(195935, reparsed!.RowsDone);
        Assert.Equal(463000, reparsed.RowsTotal);
    }

    [Fact]
    public void Worker_event_without_row_counts_remains_backward_compatible()
    {
        const string legacy = "{\"run_id\":\"run-legacy\",\"timestamp\":\"2026-01-01T00:00:00+00:00\",\"phase\":\"SAVING\"}";

        var reparsed = WorkerEvent.TryParse(legacy);

        Assert.NotNull(reparsed);
        Assert.Null(reparsed!.RowsDone);
        Assert.Null(reparsed.RowsTotal);
        Assert.DoesNotContain("rows_done", reparsed.ToJsonLine());
        Assert.DoesNotContain("rows_total", reparsed.ToJsonLine());
    }

    [Fact]
    public void Event_writer_append_mode_preserves_pre_native_progress()
    {
        var path = Path.Combine(Path.GetTempPath(), $"xlsxwin-event-append-{Guid.NewGuid():N}.jsonl");
        const string pythonEvent = "{\"run_id\":\"python\",\"timestamp\":\"2026-01-01T00:00:00+00:00\",\"phase\":\"APPLYING_EDITS\",\"rows_done\":1,\"rows_total\":1}";
        try
        {
            File.WriteAllText(path, pythonEvent + Environment.NewLine);
            using (var events = new EventWriter(path, append: true))
            {
                events.Emit(new WorkerEvent { RunId = "native", Phase = "COMPOSITE_PREFLIGHT" });
            }

            var lines = File.ReadLines(path).ToList();
            Assert.Equal(pythonEvent, lines[0]);
            Assert.Equal("native", WorkerEvent.TryParse(lines[1])!.RunId);
        }
        finally
        {
            File.Delete(path);
        }
    }

    [Fact]
    public void Worker_event_try_parse_returns_null_for_garbage()
    {
        Assert.Null(WorkerEvent.TryParse("not json"));
        Assert.Null(WorkerEvent.TryParse(""));
    }
}
