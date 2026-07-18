namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>Locates the built XlsxWinSupervisor.exe / XlsxWinWorker.exe under
/// this dev tree so tests can launch them without requiring a publish step.</summary>
internal static class BuiltExecutables
{
    public static string SupervisorExePath => FindExe("XlsxWinSupervisor");

    public static string WorkerExePath => FindExe("XlsxWinWorker");

    private static string FindExe(string projectName)
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        for (var i = 0; i < 8 && current is not null; i++)
        {
            var candidateRoot = Path.Combine(current.FullName, projectName);
            if (Directory.Exists(candidateRoot))
            {
                var found = Directory.GetFiles(candidateRoot, projectName + ".exe", SearchOption.AllDirectories)
                    .OrderByDescending(File.GetLastWriteTimeUtc)
                    .FirstOrDefault();
                if (found is not null)
                {
                    return found;
                }
            }

            current = current.Parent;
        }

        throw new FileNotFoundException(
            $"Could not locate {projectName}.exe under the supervisor solution tree, searching up from " +
            $"'{AppContext.BaseDirectory}'. Build the solution first (`dotnet build`).");
    }
}
