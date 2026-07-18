namespace XlsxWinWorker;

/// <summary>
/// Named Excel object-model constants used by the late-bound COM code in this
/// project. Late-bound `dynamic` COM has no type library to pull enum names
/// from, so these are copied from the published Excel object model
/// documentation instead of an interop assembly.
/// </summary>
internal static class ExcelConstants
{
    // MsoAutomationSecurity (Microsoft.Office.Core.MsoAutomationSecurity)
    public const int MsoAutomationSecurityForceDisable = 3;

    // Workbooks.Open's UpdateLinks parameter is a bitmask, not a bool:
    // 0 = don't update either kind of link; 3 = update both external and
    // remote references. This project only ever needs "off" or "fully on".
    public const int UpdateLinksNever = 0;
    public const int UpdateLinksAlways = 3;

    // XlCalculationState. Verified empirically via direct COM probing on this
    // machine (Office 16.0): xlDone reads back as 0, not the -4135 this file
    // originally (incorrectly, from memory) used -- that value belongs to a
    // different Excel enum entirely. Getting this wrong meant the recalc
    // step's xlDone poll never matched and always ran out its deadline, which
    // is exactly the kind of thing README.md's "Known limitations" section
    // exists to flag if it's ever in doubt again: reconfirm via COM readback,
    // don't trust memory for late-bound enum values.
    public const int XlDone = 0;
    public const int XlCalculating = 1;
    public const int XlPending = 2;
}
