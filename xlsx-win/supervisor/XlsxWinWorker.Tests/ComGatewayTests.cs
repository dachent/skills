using System.Runtime.InteropServices;

namespace XlsxWinWorker.Tests;

public class ComGatewayTests
{
    [Fact]
    public void ResourceExhaustionPoisonsAndBlocksEveryLaterDelegate()
    {
        var gateway = new ComGateway();
        var calls = 0;
        var fatal = new COMException("not enough storage", ComGateway.ResourceExhaustedHResult);

        var first = Assert.Throws<ExcelSessionPoisonedException>(() =>
            gateway.Invoke("APPLYING_EDITS", "Range.Value2", () => throw new InvalidOperationException("wrapped", fatal)));
        Assert.Equal("RESOURCE_EXHAUSTED_0X8007000E", first.Evidence.Code);
        Assert.Equal("com_boundary", first.Evidence.Origin);

        Assert.Throws<ExcelSessionPoisonedException>(() =>
            gateway.Invoke("SAVING", "Workbook.Save", () => calls++));
        Assert.Equal(0, calls);
    }

    [Fact]
    public void OrdinaryExceptionDoesNotPoison()
    {
        var gateway = new ComGateway();
        Assert.Throws<InvalidOperationException>(() => gateway.Invoke("P", "O", () => throw new InvalidOperationException("ordinary")));
        Assert.False(gateway.IsPoisoned);
    }

    [Fact]
    public void Named_fault_injection_uses_the_real_poison_latch_and_never_calls_the_delegate()
    {
        var gateway = new ComGateway("PivotCache.Refresh");
        var calls = 0;

        var fatal = Assert.Throws<ExcelSessionPoisonedException>(() =>
            gateway.Invoke("REFRESHING_PIVOTS", "PivotCache.Refresh", () => calls++));

        Assert.Equal(0, calls);
        Assert.True(gateway.IsPoisoned);
        Assert.Equal("RESOURCE_EXHAUSTED_0X8007000E", fatal.Evidence.Code);
        Assert.Equal("com_boundary", fatal.Evidence.Origin);
        Assert.Equal("PivotCache.Refresh", fatal.Evidence.Operation);
    }
}
