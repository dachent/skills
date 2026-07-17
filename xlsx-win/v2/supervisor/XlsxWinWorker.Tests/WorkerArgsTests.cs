using XlsxWinWorker;

namespace XlsxWinWorker.Tests;

public class WorkerArgsTests
{
    [Fact]
    public void Parses_three_positional_arguments()
    {
        var args = WorkerArgs.Parse(new[] { "job.json", "events.jsonl", "result.json" });

        Assert.Equal("job.json", args.JobPath);
        Assert.Equal("events.jsonl", args.EventsPath);
        Assert.Equal("result.json", args.ResultPath);
    }

    [Fact]
    public void Zero_arguments_throws_a_clear_error() => AssertThrowsClearError(Array.Empty<string>());

    [Fact]
    public void One_argument_throws_a_clear_error() => AssertThrowsClearError(new[] { "only-one.json" });

    [Fact]
    public void Two_arguments_throws_a_clear_error() => AssertThrowsClearError(new[] { "a.json", "b.jsonl" });

    [Fact]
    public void Four_arguments_throws_a_clear_error() =>
        AssertThrowsClearError(new[] { "a.json", "b.jsonl", "c.json", "d-extra.json" });

    private static void AssertThrowsClearError(string[] args)
    {
        var ex = Assert.Throws<ArgumentException>(() => WorkerArgs.Parse(args));
        Assert.Contains("Expected exactly 3 arguments", ex.Message);
    }
}
