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
    public void Worker_event_try_parse_returns_null_for_garbage()
    {
        Assert.Null(WorkerEvent.TryParse("not json"));
        Assert.Null(WorkerEvent.TryParse(""));
    }
}
