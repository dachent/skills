using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class SuspendedWorkerTests
{
    [Theory]
    [InlineData("plain", "plain")]
    [InlineData("has space", "\"has space\"")]
    [InlineData("C:\\path with space\\", "\"C:\\path with space\\\\\"")]
    [InlineData("a\"b", "\"a\\\"b\"")]
    public void Quote_uses_CreateProcess_command_line_rules(string value, string expected) =>
        Assert.Equal(expected, SuspendedWorker.Quote(value));
}
