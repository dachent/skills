using XlsxWinSupervisor;

namespace XlsxWinSupervisor.Tests;

public class SupervisorExitContractTests
{
    [Fact]
    public void Trustworthy_success_returns_zero() => Assert.Equal(0, Program.TrustedResultExitCode(true));

    [Fact]
    public void Trustworthy_failure_returns_one() => Assert.Equal(1, Program.TrustedResultExitCode(false));
}
