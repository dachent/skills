namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// A fresh temp directory created by the test itself, per safety rule 2:
/// integration tests only ever create and operate on throwaway workbooks
/// inside a temp path they create -- never any file outside it.
/// </summary>
public sealed class TestTempDir : IDisposable
{
    public string Path { get; }

    public TestTempDir()
    {
        Path = System.IO.Path.Combine(System.IO.Path.GetTempPath(), "xlsxwin-inttest-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(Path);
    }

    public string Combine(string fileName) => System.IO.Path.Combine(Path, fileName);

    public void Dispose()
    {
        try
        {
            if (Directory.Exists(Path))
            {
                Directory.Delete(Path, recursive: true);
            }
        }
        catch
        {
            // Best-effort cleanup; a leftover temp dir is not a safety issue.
        }
    }
}
