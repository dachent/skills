param(
    [string]$JsonPath
)

# CI/local smoke-test entrypoint for xlsx-win v2. Runs the real end-to-end
# certification harness (certification/run_corpus.py) against real Excel:
# router decisions, a genuine Power-Query-connection refresh through the
# built supervisor, validation contracts, and macro-policy rejection.
# Requires the supervisor solution to already be built (dotnet build
# xlsx-win/supervisor/XlsxWinSupervisor.slnx) and a Python environment with
# xlsx-win/requirements.txt installed.

$ErrorActionPreference = "Stop"
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:XLSXWIN_RUN_EXCEL_INTEGRATION_TESTS = "1"

$pythonExe = (Get-Command python -ErrorAction SilentlyContinue | Select-Object -First 1).Source
if ([string]::IsNullOrWhiteSpace($pythonExe)) {
    throw "python was not found on PATH."
}

& $pythonExe (Join-Path $scriptDir "run_corpus.py")
$exitCode = $LASTEXITCODE

if (-not [string]::IsNullOrWhiteSpace($JsonPath)) {
    $summary = [ordered]@{
        status      = if ($exitCode -eq 0) { "success" } else { "error" }
        message     = if ($exitCode -eq 0) { "xlsx-win certification corpus passed." } else { "xlsx-win certification corpus reported failures." }
        exit_code   = $exitCode
        timestamp   = (Get-Date).ToString("s")
    }

    $jsonDir = Split-Path -Path $JsonPath -Parent
    if (-not [string]::IsNullOrWhiteSpace($jsonDir) -and -not (Test-Path -LiteralPath $jsonDir)) {
        New-Item -ItemType Directory -Path $jsonDir -Force | Out-Null
    }

    $summary | ConvertTo-Json -Depth 4 | Set-Content -Path $JsonPath -Encoding UTF8
}

exit $exitCode
