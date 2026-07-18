namespace XlsxWinWorker;

/// <summary>
/// XlsxWinWorker.exe &lt;job.json path&gt; &lt;events.jsonl path&gt; &lt;result.json path&gt;
/// </summary>
public sealed record WorkerArgs(string JobPath, string EventsPath, string ResultPath)
{
    public static WorkerArgs Parse(string[] args)
    {
        if (args.Length != 3)
        {
            throw new ArgumentException(
                $"Expected exactly 3 arguments (job.json path, events.jsonl path, result.json path), got {args.Length}. " +
                "Usage: XlsxWinWorker <job.json> <events.jsonl> <result.json>");
        }

        return new WorkerArgs(args[0], args[1], args[2]);
    }
}
