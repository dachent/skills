using System.Runtime.InteropServices;

namespace XlsxWinWorker;

internal sealed record PoisonEvidence(
    string Code,
    string Origin,
    string Phase,
    string Operation,
    int HResult,
    string ExceptionType,
    string Message);

internal sealed class ExcelSessionPoisonedException : Exception
{
    public PoisonEvidence Evidence { get; }

    public ExcelSessionPoisonedException(PoisonEvidence evidence, Exception? inner = null)
        : base($"{evidence.Code}: {evidence.Message}", inner)
    {
        HResult = evidence.HResult;
        Evidence = evidence;
    }
}

/// <summary>
/// The one fatal boundary for Excel COM calls and owned RCW leases. Once an
/// 0x8007000E is observed anywhere in a wrapped exception chain, the gateway
/// latches poison atomically. Every later Invoke fails before executing its
/// delegate and Release becomes a no-op, so no Excel COM call or RCW release
/// can happen after poison.
/// </summary>
internal sealed class ComGateway
{
    internal const string ResourceExhaustionInjectionEnvVar = "XLSXWIN_TEST_INJECT_RESOURCE_EXHAUSTION_AT";

    internal const int ResourceExhaustedHResult = unchecked((int)0x8007000E);

    private int _poisoned;
    private int _trackedOwnedRcwLeases;
    private int _trackedOwnedRcwHighWater;
    private PoisonEvidence? _poisonEvidence;
    private readonly string? _resourceExhaustionInjectionOperation;
    private int _resourceExhaustionInjectionFired;

    public ComGateway(string? resourceExhaustionInjectionOperation = null)
    {
        _resourceExhaustionInjectionOperation = resourceExhaustionInjectionOperation
            ?? Environment.GetEnvironmentVariable(ResourceExhaustionInjectionEnvVar);
    }


    public bool IsPoisoned => Volatile.Read(ref _poisoned) != 0;
    public PoisonEvidence? PoisonEvidence => _poisonEvidence;
    public int TrackedOwnedRcwLeases => Volatile.Read(ref _trackedOwnedRcwLeases);
    public int TrackedOwnedRcwHighWater => Volatile.Read(ref _trackedOwnedRcwHighWater);

    public T Invoke<T>(string phase, string operation, Func<T> call)
    {
        ThrowIfPoisoned();
        try
        {
            if (string.Equals(operation, _resourceExhaustionInjectionOperation, StringComparison.Ordinal)
                && Interlocked.CompareExchange(ref _resourceExhaustionInjectionFired, 1, 0) == 0)
            {
                throw new COMException("test-only injected resource exhaustion", ResourceExhaustedHResult);
            }

            return call();
        }
        catch (Exception ex) when (FindResourceExhaustion(ex) is { } fatal)
        {
            var evidence = new PoisonEvidence(
                "RESOURCE_EXHAUSTED_0X8007000E",
                fatal is OutOfMemoryException ? "managed_allocation" : fatal is COMException ? "com_boundary" : "unknown",
                phase,
                operation,
                ResourceExhaustedHResult,
                fatal.GetType().FullName ?? fatal.GetType().Name,
                fatal.Message);
            if (Interlocked.CompareExchange(ref _poisoned, 1, 0) == 0)
            {
                _poisonEvidence = evidence;
            }
            throw new ExcelSessionPoisonedException(_poisonEvidence ?? evidence, ex);
        }
    }

    public void Invoke(string phase, string operation, Action call) =>
        Invoke<object?>(phase, operation, () => { call(); return null; });

    public dynamic Acquire(string phase, string operation, Func<dynamic> call)
    {
        var value = Invoke(phase, operation, call);
        if (value is not null && Marshal.IsComObject(value))
        {
            var current = Interlocked.Increment(ref _trackedOwnedRcwLeases);
            while (true)
            {
                var high = Volatile.Read(ref _trackedOwnedRcwHighWater);
                if (current <= high || Interlocked.CompareExchange(ref _trackedOwnedRcwHighWater, current, high) == high) break;
            }
        }
        return value!;
    }

    public void Release(object? value)
    {
        if (value is null || IsPoisoned) return;
        if (!Marshal.IsComObject(value)) return;
        Marshal.ReleaseComObject(value);
        Interlocked.Decrement(ref _trackedOwnedRcwLeases);
    }

    private void ThrowIfPoisoned()
    {
        if (IsPoisoned)
        {
            throw new ExcelSessionPoisonedException(
                _poisonEvidence ?? new PoisonEvidence(
                    "RESOURCE_EXHAUSTED_0X8007000E", "unknown", "unknown", "blocked_after_poison",
                    ResourceExhaustedHResult, nameof(ExcelSessionPoisonedException), "Excel session is poisoned."));
        }
    }

    private static Exception? FindResourceExhaustion(Exception exception)
    {
        for (Exception? current = exception; current is not null; current = current.InnerException)
        {
            if (current.HResult == ResourceExhaustedHResult) return current;
        }
        return null;
    }
}
