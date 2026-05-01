param(
    [Parameter(Mandatory = $true)]
    [string]$WorkbookPath,

    [string]$LogPath,

    [string]$JsonPath,

    [switch]$EnableMacros,

    [int]$TimeoutSeconds = 1800
)

$ErrorActionPreference = "Stop"
$global:ExitCode = 1
$excel = $null
$workbook = $null
$startTime = Get-Date
$resolvedWorkbookPath = $WorkbookPath
$logReady = $false
$saveOnClose = $false
$macroPolicy = if ($EnableMacros.IsPresent) { "enabled" } else { "disabled" }
$sharedOfficeModule = (Resolve-Path (Join-Path $PSScriptRoot '..\..\.shared\office-com\scripts\office_com_common.psm1')).Path

Import-Module $sharedOfficeModule -Force -DisableNameChecking

function Ensure-ParentDirectory {
    param(
        [string]$PathValue
    )

    $dir = Split-Path -Path $PathValue -Parent
    if ([string]::IsNullOrWhiteSpace($dir) -eq $false -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

function Get-AbsolutePath {
    param(
        [string]$PathValue
    )

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        return $null
    }

    try {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    catch {
        return $PathValue
    }
}

function New-ArtifactPath {
    param(
        [string]$BasePath,
        [string]$Kind,
        [string]$Extension
    )

    $leafBase = [System.IO.Path]::GetFileNameWithoutExtension($BasePath)
    if ([string]::IsNullOrWhiteSpace($leafBase)) {
        $leafBase = "workbook"
    }

    $safeLeaf = [regex]::Replace($leafBase, "[^A-Za-z0-9._-]", "_")
    $stamp = Get-Date -Format "yyyyMMdd-HHmmssfff"
    $suffix = [guid]::NewGuid().ToString("N").Substring(0, 8)
    $fileName = "{0}-{1}-{2}-{3}.{4}" -f $safeLeaf, $Kind, $stamp, $suffix, $Extension
    return Join-Path ([System.IO.Path]::GetTempPath()) $fileName
}

function Resolve-ArtifactPath {
    param(
        [string]$RequestedPath,
        [string]$BasePath,
        [string]$Kind,
        [string]$Extension
    )

    if ([string]::IsNullOrWhiteSpace($RequestedPath)) {
        return (New-ArtifactPath -BasePath $BasePath -Kind $Kind -Extension $Extension)
    }

    return (Get-AbsolutePath -PathValue $RequestedPath)
}

function Write-Log {
    param(
        [string]$Message,
        [string]$Level = "INFO"
    )

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$timestamp [$Level] $Message"
    Write-Host $line
    if ($logReady) {
        Add-Content -Path $LogPath -Value $line
    }
}

function Get-ErrorInfo {
    param(
        [System.Management.Automation.ErrorRecord]$Record
    )

    $rawMessage = $Record.Exception.Message
    $normalized = $rawMessage.ToLowerInvariant()
    $errorKind = "runtime_error"
    $friendlyMessage = $rawMessage

    if ($rawMessage.StartsWith("OFFICE_PRECHECK::")) {
        $parts = $rawMessage.Split("::", 3)
        $errorKind = if ($parts.Length -ge 2) { $parts[1] } else { "excel_com_unavailable" }
        $friendlyMessage = if ($parts.Length -ge 3) { $parts[2] } else { "Excel COM automation is unavailable in this session." }
    }
    elseif (
        $normalized.Contains("0x80070520") -or
        $normalized.Contains("80070520") -or
        $normalized.Contains("specified logon session does not exist") -or
        $normalized.Contains("retrieving the com class factory")
    ) {
        $errorKind = "excel_com_unavailable"
        $friendlyMessage = "Excel COM automation is unavailable in this session. Run refresh_excel.ps1 from an interactive Windows desktop session or outside the Codex sandbox."
    }
    elseif (
        $normalized.Contains("class not registered") -or
        $normalized.Contains("activex component can't create object")
    ) {
        $errorKind = "excel_not_installed"
        $friendlyMessage = "Excel COM automation could not be created. Confirm that Microsoft 365 Excel desktop is installed and registered correctly."
    }
    elseif (
        $normalized.Contains("workbook path does not exist") -or
        $normalized.Contains("cannot find path")
    ) {
        $errorKind = "missing_workbook"
        $friendlyMessage = "Workbook path does not exist: $WorkbookPath"
    }
    elseif ($normalized.Contains("timed out waiting for excel calculation")) {
        $errorKind = "calculation_timeout"
    }
    elseif (
        $normalized.Contains("call was rejected by callee") -or
        $normalized.Contains("application is busy") -or
        $normalized.Contains("message filter indicated that the application is busy")
    ) {
        $errorKind = "excel_busy"
        $friendlyMessage = "Excel is busy and did not accept the automation call. Close blocking prompts or Excel dialogs and retry."
    }
    elseif (
        $normalized.Contains("workbook opened read-only") -or
        $normalized.Contains("read-only")
    ) {
        $errorKind = "read_only_workbook"
        $friendlyMessage = "The workbook opened read-only. Close other Excel sessions or clear the file's read-only state before refreshing."
    }
    elseif (
        $normalized.Contains("sharing violation") -or
        $normalized.Contains("used by another process")
    ) {
        $errorKind = "file_locked"
        $friendlyMessage = "The workbook appears to be locked by another process. Close other Excel instances or release the file lock and retry."
    }

    [pscustomobject]@{
        kind = $errorKind
        message = $friendlyMessage
        raw_message = $rawMessage
    }
}

function Write-StatusJson {
    param(
        [string]$Status,
        [string]$Message,
        [string]$ResolvedWorkbookPath = $null,
        [int]$DurationSeconds = 0,
        [string]$ErrorKind = $null,
        [int]$ConnectionCount = 0
    )

    $payload = [ordered]@{
        status = $Status
        message = $Message
        workbook = $ResolvedWorkbookPath
        macro_policy = $macroPolicy
        log_path = (Get-AbsolutePath -PathValue $LogPath)
        json_path = (Get-AbsolutePath -PathValue $JsonPath)
        connection_count = $ConnectionCount
        duration_seconds = $DurationSeconds
        timestamp = (Get-Date).ToString("s")
        exit_code = $global:ExitCode
    }

    if ([string]::IsNullOrWhiteSpace($ErrorKind) -eq $false) {
        $payload.error_kind = $ErrorKind
    }

    $payload | ConvertTo-Json -Depth 4 | Set-Content -Path $JsonPath -Encoding UTF8
}

function Wait-ForCalculationComplete {
    param(
        $ExcelApplication,
        [datetime]$Deadline
    )

    while ($ExcelApplication.CalculationState -ne 0) {
        if ((Get-Date) -gt $Deadline) {
            throw "Timed out waiting for Excel calculation to complete after $TimeoutSeconds seconds."
        }

        Start-Sleep -Milliseconds 500
    }
}

try {
    $LogPath = Resolve-ArtifactPath -RequestedPath $LogPath -BasePath $WorkbookPath -Kind "refresh" -Extension "log"
    $JsonPath = Resolve-ArtifactPath -RequestedPath $JsonPath -BasePath $WorkbookPath -Kind "refresh" -Extension "json"

    Ensure-ParentDirectory -PathValue $LogPath
    Ensure-ParentDirectory -PathValue $JsonPath

    Set-Content -Path $LogPath -Value "" -Encoding UTF8
    $logReady = $true

    Write-Log "Starting Excel refresh job."
    Write-Log "Workbook argument: $WorkbookPath"
    Write-Log "Log file: $LogPath"
    Write-Log "JSON file: $JsonPath"
    Write-Log "TimeoutSeconds: $TimeoutSeconds"
    Write-Log "Macro policy: $macroPolicy"

    if (-not (Test-Path -LiteralPath $WorkbookPath)) {
        throw "Workbook path does not exist: $WorkbookPath"
    }

    $resolvedWorkbookPath = (Resolve-Path -LiteralPath $WorkbookPath -ErrorAction Stop).Path
    Write-Log "Resolved workbook path: $resolvedWorkbookPath"

    $preflight = Get-OfficeComPreflightResult -Apps @('Excel')
    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $preflight -AppName 'Excel'
    if ($null -ne $failureInfo) {
        throw "OFFICE_PRECHECK::$($failureInfo.error_kind)::$($failureInfo.message)"
    }

    $excel = New-Object -ComObject Excel.Application
    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.EnableEvents = $false
    $excel.AskToUpdateLinks = $false
    $excel.Interactive = $false
    $excel.ScreenUpdating = $false
    $excel.AutomationSecurity = if ($EnableMacros.IsPresent) { 1 } else { 3 }

    Write-Log "Excel COM instance created."

    $workbook = $excel.Workbooks.Open($resolvedWorkbookPath, 0, $false)
    Write-Log "Workbook opened."

    if ($workbook.ReadOnly) {
        throw "Workbook opened read-only: $resolvedWorkbookPath"
    }

    try {
        # xlCalculationAutomatic = -4105
        $excel.Calculation = -4105
    }
    catch {
        Write-Log "Unable to force automatic calculation: $($_.Exception.Message)" "WARN"
    }

    Write-Log "Calling RefreshAll()."
    $workbook.RefreshAll()

    try {
        Write-Log "Waiting for async queries with CalculateUntilAsyncQueriesDone()."
        $excel.CalculateUntilAsyncQueriesDone()
    }
    catch {
        Write-Log "CalculateUntilAsyncQueriesDone() raised: $($_.Exception.Message)" "WARN"
    }

    Write-Log "Calling CalculateFullRebuild()."
    $excel.CalculateFullRebuild()

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    Wait-ForCalculationComplete -ExcelApplication $excel -Deadline $deadline

    Write-Log "Excel calculation state is Done."

    $connectionCount = 0
    try {
        $connectionCount = [int]$workbook.Connections.Count
    }
    catch {
        $connectionCount = 0
    }

    if ($connectionCount -gt 0) {
        Write-Log "Workbook has $connectionCount connection(s)."
    }
    else {
        Write-Log "Workbook has no workbook connections."
    }

    Write-Log "Saving workbook."
    $workbook.Save()
    $saveOnClose = $false

    $duration = [int]((Get-Date) - $startTime).TotalSeconds
    Write-Log "Workbook saved successfully."
    Write-Log "Job completed successfully in $duration second(s)."

    $global:ExitCode = 0
    Write-StatusJson -Status "success" -Message "Workbook refreshed and saved successfully." -ResolvedWorkbookPath $resolvedWorkbookPath -DurationSeconds $duration -ConnectionCount $connectionCount
}
catch {
    $duration = [int]((Get-Date) - $startTime).TotalSeconds
    $errorInfo = Get-ErrorInfo -Record $_

    Write-Log "Job failed after $duration second(s)." "ERROR"
    Write-Log "Error: $($errorInfo.message)" "ERROR"

    if ($errorInfo.raw_message -ne $errorInfo.message) {
        Write-Log "Original error: $($errorInfo.raw_message)" "WARN"
    }

    if ($_.ScriptStackTrace) {
        Write-Log "Stack: $($_.ScriptStackTrace)" "ERROR"
    }

    $global:ExitCode = 2
    Write-StatusJson -Status "error" -Message $errorInfo.message -ResolvedWorkbookPath $resolvedWorkbookPath -DurationSeconds $duration -ErrorKind $errorInfo.kind
}
finally {
    if ($workbook -ne $null) {
        try {
            Write-Log "Closing workbook."
            $workbook.Close($saveOnClose) | Out-Null
        }
        catch {
            Write-Log "Failed to close workbook cleanly: $($_.Exception.Message)" "WARN"
        }
    }

    if ($excel -ne $null) {
        try {
            Write-Log "Quitting Excel."
            $excel.Quit()
        }
        catch {
            Write-Log "Failed to quit Excel cleanly: $($_.Exception.Message)" "WARN"
        }
    }

    if ($workbook -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($workbook)
    }

    if ($excel -ne $null) {
        [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($excel)
    }

    [gc]::Collect()
    [gc]::WaitForPendingFinalizers()

    Write-Log "Exiting with code $global:ExitCode."
    exit $global:ExitCode
}
