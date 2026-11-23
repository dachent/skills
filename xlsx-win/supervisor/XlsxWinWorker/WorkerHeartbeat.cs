using XlsxWinContracts;
using Timer = System.Threading.Timer;

namespace XlsxWinWorker;

internal sealed class WorkerHeartbeat : IDisposable
{
    private readonly EventWriter _events;
    private readonly string _runId;
    private readonly Timer _timer;
    private readonly object _sync = new();
    private bool _stopped;

    public WorkerHeartbeat(EventWriter events, string runId, TimeSpan? interval = null)
    {
        _events = events;
        _runId = runId;
        var period = interval ?? TimeSpan.FromSeconds(5);
        _timer = new Timer(OnTick, null, period, period);
    }

    public Exception? Fault { get; private set; }

    private void OnTick(object? state)
    {
        lock (_sync)
        {
            if (_stopped)
            {
                return;
            }
            try
            {
                _events.EmitHeartbeat(_runId);
            }
            catch (Exception ex)
            {
                Fault = ex;
                _stopped = true;
                _timer.Dispose();
            }
        }
    }

    public void Dispose()
    {
        lock (_sync)
        {
            if (_stopped)
            {
                return;
            }
            _stopped = true;
            _timer.Dispose();
        }
    }
}
