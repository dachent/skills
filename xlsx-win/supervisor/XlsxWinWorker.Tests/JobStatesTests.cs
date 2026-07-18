using XlsxWinContracts;

namespace XlsxWinWorker.Tests;

/// <summary>Mirrors control_plane/tests/test_state_machine.py's key assertions,
/// against the C# port in JobStates, to keep the two definitions honest.</summary>
public class JobStatesTests
{
    [Fact]
    public void Terminal_states_match_python_port()
    {
        Assert.True(JobStates.IsTerminal("SUCCEEDED"));
        Assert.True(JobStates.IsTerminal("FAILED"));
        Assert.True(JobStates.IsTerminal("TIMED_OUT"));
        Assert.True(JobStates.IsTerminal("CANCELLED"));
        Assert.False(JobStates.IsTerminal("REFRESHING_CONNECTIONS"));
    }

    [Fact]
    public void Cannot_transition_from_a_terminal_state()
    {
        Assert.False(JobStates.CanTransition("SUCCEEDED", "SAVING"));
        Assert.False(JobStates.CanTransition("FAILED", "CALCULATING"));
    }

    [Fact]
    public void Can_always_abort_to_failed_timed_out_or_cancelled()
    {
        Assert.True(JobStates.CanTransition("OPENING_WORKBOOK", "FAILED"));
        Assert.True(JobStates.CanTransition("CALCULATING", "TIMED_OUT"));
        Assert.True(JobStates.CanTransition("STARTING_EXCEL", "CANCELLED"));
    }

    [Fact]
    public void Cannot_move_backward_a_phase()
    {
        Assert.False(JobStates.CanTransition("SAVING", "OPENING_WORKBOOK"));
    }

    [Fact]
    public void Compute_phase_states_may_interleave_and_repeat()
    {
        Assert.True(JobStates.CanTransition("CALCULATING", "REFRESHING_CONNECTIONS"));
        Assert.True(JobStates.CanTransition("REFRESHING_CONNECTIONS", "CALCULATING"));
        Assert.True(JobStates.CanTransition("RUNNING_APPROVED_MACRO", "CALCULATING"));
    }

    [Fact]
    public void Unknown_state_throws()
    {
        Assert.Throws<ArgumentException>(() => JobStates.IsTerminal("NOT_A_REAL_STATE"));
        Assert.Throws<ArgumentException>(() => JobStates.CanTransition("NOT_A_REAL_STATE", "FAILED"));
    }

    [Fact]
    public void Transition_returns_target_state_or_throws()
    {
        Assert.Equal("OPENING_WORKBOOK", JobStates.Transition("STARTING_EXCEL", "OPENING_WORKBOOK"));
        Assert.Throws<InvalidOperationException>(() => JobStates.Transition("SAVING", "OPENING_WORKBOOK"));
    }
}
