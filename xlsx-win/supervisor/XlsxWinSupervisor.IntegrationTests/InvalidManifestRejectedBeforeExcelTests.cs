using Xunit;

namespace XlsxWinSupervisor.IntegrationTests;

/// <summary>
/// Invalid-manifest-rejected-before-Excel: a job manifest that fails #34's
/// schema validation (here: an unrecognized step "type" discriminator, the
/// same UNKNOWN_STEP_TYPE failure category control_plane/schemas.py
/// classifies on the Python side) must be rejected before any Excel process
/// is ever started. This supervisor does not itself schema-validate against
/// job.schema.json (see README.md, "Known gap vs job.schema.json") -- but
/// its own JobManifest model is a [JsonPolymorphic] step-type discriminator
/// with no fallback, so an unrecognized "type" value fails to deserialize at
/// all, which Program.cs's own top-level try/catch turns into exit code 2
/// before EnsureParentDirectory/truncation or the worker process launch ever
/// run. Confirmed empirically (not just asserted from reading the code)
/// against the real built XlsxWinSupervisor.exe before this test was
/// written.
/// </summary>
public class InvalidManifestRejectedBeforeExcelTests
{
    public InvalidManifestRejectedBeforeExcelTests()
    {
        ExcelIntegrationGate.PreflightOrSkip();
    }

    [SkippableFact]
    public void Manifest_with_unknown_step_type_is_rejected_before_any_excel_process_starts()
    {
        using var tempDir = new TestTempDir();
        var jobPath = tempDir.Combine("job.json");
        var eventsPath = tempDir.Combine("events.jsonl");
        var resultPath = tempDir.Combine("result.json");

        // "delete_everything" is not one of job.schema.json's five known step
        // types (open/refresh/recalc/run_approved_macro/save_as), and is not
        // registered as a JsonDerivedType on XlsxWinContracts.JobStep either.
        const string invalidManifestJson = """
        {
          "schema_version": "2.0",
          "idempotency_key": "invalid-manifest-test",
          "steps": [
            { "type": "delete_everything", "workbook_path": "irrelevant" }
          ]
        }
        """;
        File.WriteAllText(jobPath, invalidManifestJson);

        var runResult = SupervisorRunner.Run(jobPath, eventsPath, resultPath, TimeSpan.FromSeconds(60));

        var diagnostics =
            $"exitCode={runResult.ExitCode} elapsed={runResult.Elapsed}\n" +
            $"stdout={runResult.Stdout}\nstderr={runResult.Stderr}";

        try
        {
            Assert.True(2 == runResult.ExitCode,
                $"Expected exit code 2 (argument/manifest-parse error), per README.md's exit-code " +
                $"contract.\n{diagnostics}");

            Assert.Contains("delete_everything", runResult.Stderr);

            // Neither artifact should exist at all: Program.cs only creates/
            // truncates them (EnsureParentDirectory + File.WriteAllText)
            // *after* JobManifest.Parse succeeds, so their complete absence
            // is itself evidence parsing failed before that point -- not
            // just that the supervisor eventually reported an error.
            Assert.False(File.Exists(eventsPath),
                $"events.jsonl should not exist -- manifest parsing must fail before the supervisor " +
                $"ever creates/truncates it or launches the worker.\n{diagnostics}");
            Assert.False(File.Exists(resultPath),
                $"result.json should not exist for the same reason.\n{diagnostics}");
        }
        finally
        {
            // Safety rule 5, "never launched" variant: confirm zero
            // EXCEL.EXE processes exist at all. This is stronger than just
            // checking the supervisor's reported outcome -- it distinguishes
            // "Excel never started" (what this test claims) from "Excel
            // started and was then successfully cleaned up" (a different,
            // weaker claim that would still leave this test's title false).
            ExcelIntegrationGate.AssertNoExcelProcessSurvives();
        }
    }
}
