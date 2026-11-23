using XlsxWinContracts;
using Timer = System.Threading.Timer;

namespace XlsxWinWorker;

internal sealed class WorkerHeartbeat : IDisposable
{
    private readonly EventWriter _events;
    private readonly string _runId;
    private readonly Timer _timer;
    private readonly object _sync = new();
    private readonly Func<Exception?>? _faultInjector;
    private Exception? _fault;
    private bool _stopped;

    public WorkerHeartbeat(EventWriter events, string runId, TimeSpan? interval = null,
        Func<Exception?>? faultInjector = null)
    {
        _events = events;
        _runId = runId;
        _faultInjector = faultInjector;
        var period = interval ?? TimeSpan.FromSeconds(5);
        _timer = new Timer(OnTick, null, period, period);
    }

    public Exception? Fault
    {
        get
        {
            lock (_sync)
            {
                return _fault;
            }
        }
    }

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
                if (_faultInjector?.Invoke() is Exception injected)
                {
                    throw injected;
                }
                _events.EmitHeartbeat(_runId);
            }
            catch (Exception ex)
            {
                _fault = ex;
                _stopped = true;
                _timer.Dispose();
                Console.Error.WriteLine($"WORKER_HEARTBEAT_WRITE_FAILED: {ex.Message}");
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
