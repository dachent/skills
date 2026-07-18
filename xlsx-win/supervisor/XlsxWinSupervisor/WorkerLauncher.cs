namespace XlsxWinSupervisor;

/// <summary>Resolves the path to XlsxWinWorker.exe.</summary>
public static class WorkerLauncher
{
    public const string WorkerPathEnvVar = "XLSXWIN_WORKER_EXE_PATH";

    public static string ResolveWorkerExePath()
    {
        var overridePath = Environment.GetEnvironmentVariable(WorkerPathEnvVar);
        if (!string.IsNullOrWhiteSpace(overridePath))
        {
            if (!File.Exists(overridePath))
            {
                throw new FileNotFoundException(
                    $"{WorkerPathEnvVar} is set to '{overridePath}' but that file does not exist.", overridePath);
            }

            return overridePath;
        }

        var supervisorDir = AppContext.BaseDirectory;

        // Preferred layout: XlsxWinWorker.exe published/copied alongside
        // XlsxWinSupervisor.exe.
        var sibling = Path.Combine(supervisorDir, "XlsxWinWorker.exe");
        if (File.Exists(sibling))
        {
            return sibling;
        }

        // Dev-time fallback: running from bin/<Config>/net10.0-windows under
        // the source tree, with XlsxWinWorker built as a sibling project.
        var devCandidate = FindDevBuildOutput(supervisorDir);
        if (devCandidate is not null)
        {
            return devCandidate;
        }

        throw new FileNotFoundException(
            $"Could not locate XlsxWinWorker.exe next to XlsxWinSupervisor.exe (dir: '{supervisorDir}') or under a " +
            $"sibling XlsxWinWorker project. Set {WorkerPathEnvVar} explicitly, or build/publish XlsxWinWorker into " +
            "the same output directory as XlsxWinSupervisor.");
    }

    private static string? FindDevBuildOutput(string startDir)
    {
        var current = new DirectoryInfo(startDir);
        for (var i = 0; i < 8 && current is not null; i++)
        {
            var candidateRoot = Path.Combine(current.FullName, "XlsxWinWorker");
            if (Directory.Exists(candidateRoot))
            {
                var found = Directory.GetFiles(candidateRoot, "XlsxWinWorker.exe", SearchOption.AllDirectories)
                    .OrderByDescending(File.GetLastWriteTimeUtc)
                    .FirstOrDefault();
                if (found is not null)
                {
                    return found;
                }
            }

            current = current.Parent;
        }

        return null;
    }
}
