namespace XlsxWinWorker;

/// <summary>
/// Minimal STA message pump. Excel COM automation from an out-of-process
/// client relies on the client's STA apartment periodically processing
/// Windows messages so marshaled calls and any callbacks Excel makes back
/// into the client can be serviced -- a bare `Thread.Sleep` polling loop on
/// an STA thread can starve that. `Application.DoEvents()` (from
/// System.Windows.Forms, enabled via UseWindowsForms in the csproj) is the
/// simplest correct way to pump messages without standing up a full message
/// loop / hidden window ourselves. This is deliberately the whole of this
/// increment's "message pump" support -- IMessageFilter-based COM retry
/// handling is explicitly deferred (see README.md).
/// </summary>
internal static class MessagePump
{
    public static void Pump()
    {
        System.Windows.Forms.Application.DoEvents();
    }

    /// <summary>Sleep for the given duration while still pumping messages
    /// periodically, instead of blocking the STA thread outright.</summary>
    public static void PumpingDelay(TimeSpan duration)
    {
        var deadline = DateTime.UtcNow + duration;
        while (DateTime.UtcNow < deadline)
        {
            Pump();
            Thread.Sleep(50);
        }
    }
}
