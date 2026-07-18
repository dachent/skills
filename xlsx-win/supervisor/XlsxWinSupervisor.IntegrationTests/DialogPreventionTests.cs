using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Proves, via COM readback on the exact ExcelSession type the real worker
/// uses, that the dialog-prevention properties from RFC 0002 decision 7 are
/// actually set -- not just assumed because the code that sets them exists.
/// </summary>
public class DialogPreventionTests
{
    public DialogPreventionTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Dialog_prevention_properties_are_set_and_confirmed_via_com_readback()
    {
        using var session = new XlsxWinWorker.ExcelSession();

        try
        {
            session.Start();

            var (displayAlerts, askToUpdateLinks, automationSecurity) = session.ReadDialogPreventionState();

            Assert.False(displayAlerts, "DisplayAlerts should be false.");
            Assert.False(askToUpdateLinks, "AskToUpdateLinks should be false.");
            Assert.Equal(XlsxWinWorker.ExcelConstants.MsoAutomationSecurityForceDisable, automationSecurity);
        }
        finally
        {
            session.Dispose();
            ExcelIntegrationGate.AssertNoExcelProcessSurvives();
        }
    }
}
