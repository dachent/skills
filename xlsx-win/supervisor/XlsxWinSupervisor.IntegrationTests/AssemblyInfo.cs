using Xunit;

// These tests all drive real Excel COM automation and the safety rules
// require them to run one at a time (one active job/worker at a time, by
// construction) -- never in parallel with each other.
[assembly: CollectionBehavior(DisableTestParallelization = true)]
