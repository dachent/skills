namespace XlsxWinWorker;

/// <summary>
/// XlsxWinWorker.exe &lt;job&gt; &lt;events&gt; &lt;result&gt; &lt;control-pipe-name&gt;.
/// The control pipe is mandatory: a worker must never open a workbook before
/// the supervisor acknowledges exact Excel PID containment.
/// </summary>
public sealed record WorkerArgs(string JobPath, string EventsPath, string ResultPath, string ControlPipeName)
{
    public static WorkerArgs Parse(string[] args)
    {
        if (args.Length != 4 || string.IsNullOrWhiteSpace(args[3]))
        {
            throw new ArgumentException(
                $"Expected exactly 4 arguments (job.json path, events.jsonl path, result.json path, control pipe name), got {args.Length}. " +
                "Usage: XlsxWinWorker <job.json> <events.jsonl> <result.json> <control-pipe-name>");
        }
        return new WorkerArgs(args[0], args[1], args[2], args[3]);
    }
}
