using XlsxWinWorker;

namespace XlsxWinWorker.Tests;

/// <summary>
/// Pure logic tests for ComMessageFilter's retry policy -- no COM, no Excel,
/// no CoRegisterMessageFilter call. Exercises the IOleMessageFilter methods
/// directly against the interface's own well-known constants (see the
/// interface's Guid/method-shape doc comment for why those aren't
/// reproduced as named constants here: this test intentionally uses the raw
/// literal values an actual COM caller would pass, the same way the
/// production code's own doc comments describe them).
/// </summary>
public class ComMessageFilterTests
{
    private const int ServerCallRejected = 1;
    private const int ServerCallRetryLater = 2;

    [Fact]
    public void HandleInComingCall_always_returns_ServerCallIsHandled()
    {
        var filter = new ComMessageFilter();

        Assert.Equal(0, filter.HandleInComingCall(0, IntPtr.Zero, 0, IntPtr.Zero));
    }

    [Fact]
    public void MessagePending_always_returns_PendingMsgWaitDefProcess()
    {
        var filter = new ComMessageFilter();

        Assert.Equal(2, filter.MessagePending(IntPtr.Zero, 0, 0));
    }

    [Fact]
    public void RetryRejectedCall_with_ServerCallRejected_cancels_immediately_and_does_not_count_as_a_retry()
    {
        var filter = new ComMessageFilter();

        var outcome = filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRejected);

        Assert.Equal(-1, outcome);
        Assert.Equal(0, filter.RetryAttempts);
    }

    [Fact]
    public void RetryRejectedCall_with_ServerCallRetryLater_returns_a_short_positive_delay_and_counts_the_attempt()
    {
        var filter = new ComMessageFilter();

        var outcome = filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRetryLater);

        Assert.True(outcome > 0);
        Assert.Equal(1, filter.RetryAttempts);
    }

    [Fact]
    public void RetryRejectedCall_cancels_once_MaxRetryAttempts_is_exceeded()
    {
        var filter = new ComMessageFilter();

        for (var i = 0; i < ComMessageFilter.MaxRetryAttempts; i++)
        {
            var outcome = filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRetryLater);
            Assert.True(outcome > 0, $"Attempt {i + 1} (within the bound) should still be retried.");
        }

        var overBound = filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRetryLater);

        Assert.Equal(-1, overBound);
        Assert.Equal(ComMessageFilter.MaxRetryAttempts + 1, filter.RetryAttempts);
    }

    [Fact]
    public void ResetRetryAttempts_zeroes_the_counter_for_the_next_step()
    {
        var filter = new ComMessageFilter();
        filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRetryLater);
        filter.RetryRejectedCall(IntPtr.Zero, 0, ServerCallRetryLater);
        Assert.Equal(2, filter.RetryAttempts);

        filter.ResetRetryAttempts();

        Assert.Equal(0, filter.RetryAttempts);
    }

    [Fact]
    public void RetryRejectedCall_with_an_unrecognized_reject_type_fails_closed()
    {
        var filter = new ComMessageFilter();

        var outcome = filter.RetryRejectedCall(IntPtr.Zero, 0, dwRejectType: 99);

        Assert.Equal(-1, outcome);
    }
}
