using System.Text.Json;
using System.Text.Json.Serialization;

namespace XlsxWinContracts;

/// <summary>
/// C# model of xlsx-win/schemas/result.schema.json from issue #34.
///
/// "Ok" is computed by <see cref="Build"/>, mirroring
/// control_plane/result_contract.py's compute_ok/build_result: it is never an
/// independently-settable input, so nothing upstream can mark a job "ok" that
/// did not actually succeed.
/// </summary>
public sealed class ResultDocument
{
    [JsonPropertyName("schema_version")]
    public string SchemaVersion { get; set; } = "2.0";

    [JsonPropertyName("run_id")]
    public string RunId { get; set; } = "";

    [JsonPropertyName("idempotency_key")]
    public string IdempotencyKey { get; set; } = "";

    [JsonPropertyName("final_state")]
    public string FinalState { get; set; } = "FAILED";

    [JsonPropertyName("steps")]
    public List<StepResult> Steps { get; set; } = new();

    [JsonPropertyName("invariants")]
    public List<InvariantResult> Invariants { get; set; } = new();

    [JsonPropertyName("ok")]
    public bool Ok { get; set; }

    /// <summary>True iff every step succeeded and every declared invariant passed.
    /// Exact port of result_contract.compute_ok.</summary>
    public static bool ComputeOk(IReadOnlyList<StepResult> steps, IReadOnlyList<InvariantResult> invariants)
    {
        if (steps.Any(s => s.Status != "succeeded"))
        {
            return false;
        }

        if (invariants.Any(i => !i.Passed))
        {
            return false;
        }

        return true;
    }

    /// <summary>Build a result document with Ok computed from steps/invariants,
    /// exactly like result_contract.build_result. This is the only supported way
    /// to construct a result with a trustworthy Ok value.</summary>
    public static ResultDocument Build(
        string runId,
        string idempotencyKey,
        string finalState,
        List<StepResult> steps,
        List<InvariantResult>? invariants = null)
    {
        invariants ??= new List<InvariantResult>();
        return new ResultDocument
        {
            RunId = runId,
            IdempotencyKey = idempotencyKey,
            FinalState = finalState,
            Steps = steps,
            Invariants = invariants,
            Ok = ComputeOk(steps, invariants),
        };
    }

    public string ToJson() => JsonSerializer.Serialize(this, JsonDefaults.Options);

    public static ResultDocument Parse(string json) =>
        JsonSerializer.Deserialize<ResultDocument>(json, JsonDefaults.Options)
        ?? throw new InvalidOperationException("Result document deserialized to null.");
}

public sealed class StepResult
{
    [JsonPropertyName("step_index")]
    public int StepIndex { get; set; }

    [JsonPropertyName("type")]
    public string Type { get; set; } = "";

    [JsonPropertyName("status")]
    public string Status { get; set; } = "failed"; // succeeded | failed | skipped

    [JsonPropertyName("message")]
    public string? Message { get; set; }

    [JsonPropertyName("error")]
    public ErrorDetail? Error { get; set; }
}

public sealed class InvariantResult
{
    [JsonPropertyName("name")]
    public string Name { get; set; } = "";

    [JsonPropertyName("passed")]
    public bool Passed { get; set; }

    [JsonPropertyName("message")]
    public string? Message { get; set; }
}

public sealed class ErrorDetail
{
    [JsonPropertyName("code")]
    public string Code { get; set; } = "";

    [JsonPropertyName("message")]
    public string Message { get; set; } = "";

    [JsonPropertyName("details")]
    public Dictionary<string, object?> Details { get; set; } = new();
}
