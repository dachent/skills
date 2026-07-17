namespace XlsxWinSupervisor;

/// <summary>
/// XlsxWinSupervisor.exe &lt;job.json path&gt; &lt;events.jsonl path&gt; &lt;result.json path&gt;
///
/// The supervisor forwards these same three paths verbatim to XlsxWinWorker --
/// see README.md "Job/result JSON file-path contract".
/// </summary>
public sealed record SupervisorArgs(string JobPath, string EventsPath, string ResultPath)
{
    public static SupervisorArgs Parse(string[] args)
    {
        if (args.Length != 3)
        {
            throw new ArgumentException(
                $"Expected exactly 3 arguments (job.json path, events.jsonl path, result.json path), got {args.Length}. " +
                "Usage: XlsxWinSupervisor <job.json> <events.jsonl> <result.json>");
        }

        return new SupervisorArgs(args[0], args[1], args[2]);
    }
}
