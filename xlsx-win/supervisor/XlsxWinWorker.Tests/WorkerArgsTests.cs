using XlsxWinWorker;

namespace XlsxWinWorker.Tests;

public class WorkerArgsTests
{
    [Fact]
    public void Parses_four_positional_arguments()
    {
        var args = WorkerArgs.Parse(new[] { "job.json", "events.jsonl", "result.json", "pipe-name" });
        Assert.Equal("job.json", args.JobPath);
        Assert.Equal("events.jsonl", args.EventsPath);
        Assert.Equal("result.json", args.ResultPath);
        Assert.Equal("pipe-name", args.ControlPipeName);
    }

    [Theory]
    [InlineData()]
    [InlineData("one")]
    [InlineData("one", "two")]
    [InlineData("one", "two", "three")]
    [InlineData("one", "two", "three", "four", "five")]
    public void Wrong_argument_count_throws_a_clear_error(params string[] args)
    {
        var ex = Assert.Throws<ArgumentException>(() => WorkerArgs.Parse(args));
        Assert.Contains("Expected exactly 4 arguments", ex.Message);
    }
}
