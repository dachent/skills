namespace XlsxWinSupervisor.Tests;

public class SupervisorEventPreservationTests
{
    [Theory]
    [InlineData(null, false)]
    [InlineData("", false)]
    [InlineData("0", false)]
    [InlineData("true", false)]
    [InlineData("1", true)]
    public void Only_explicit_append_mode_preserves_existing_worker_events(string? value, bool expected)
    {
        Assert.Equal(expected, Program.ShouldPreserveExistingEvents(value));
    }
}
