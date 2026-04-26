[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('self-test', 'refresh', 'power-query')]
    [string]$Action,

    [string]$WorkbookPath,
    [string]$LogPath,
    [string]$JsonPath,
    [switch]$EnableMacros,
    [int]$TimeoutSeconds = 1800,

    [ValidateSet('upsert-query', 'load-worksheet', 'load-model', 'delete-query')]
    [string]$PowerQueryAction,
    [string]$QueryName,
    [string]$MFormula,
    [string]$MFormulaPath,
    [string]$WorksheetName,
    [string]$StartCell = 'A1'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$sharedModulePath = (Resolve-Path (Join-Path $PSScriptRoot '..\..\.shared\office-com\scripts\office_com_common.psm1')).Path
Import-Module $sharedModulePath -Force -DisableNameChecking

function Write-ResultAndExit {
    param(
        [Parameter(Mandatory)]
        [hashtable]$Payload,

        [Parameter(Mandatory)]
        [int]$ExitCode
    )

    $Payload.exit_code = $ExitCode
    $Payload | ConvertTo-Json -Depth 10
    exit $ExitCode
}

function Assert-Required {
    param(
        [string]$Value,
        [string]$Name
    )

    if ([string]::IsNullOrWhiteSpace($Value)) {
        throw "Missing required argument: $Name"
    }
}

function Get-ActionScript {
    switch ($Action) {
        'self-test' { return (Join-Path $PSScriptRoot 'self_test_xlsx_win.ps1') }
        'refresh' { return (Join-Path $PSScriptRoot 'refresh_excel.ps1') }
        'power-query' { return (Join-Path $PSScriptRoot 'power_query_excel.ps1') }
        default { throw "Unsupported action: $Action" }
    }
}

function Get-ActionArguments {
    switch ($Action) {
        'self-test' {
            $args = @()
            if (-not [string]::IsNullOrWhiteSpace($JsonPath)) { $args += @('-JsonPath', $JsonPath) }
            if ($EnableMacros.IsPresent) { $args += '-EnableMacros' }
            return $args
        }
        'refresh' {
            Assert-Required -Value $WorkbookPath -Name 'WorkbookPath'
            $args = @('-WorkbookPath', $WorkbookPath, '-TimeoutSeconds', [string]$TimeoutSeconds)
            if (-not [string]::IsNullOrWhiteSpace($LogPath)) { $args += @('-LogPath', $LogPath) }
            if (-not [string]::IsNullOrWhiteSpace($JsonPath)) { $args += @('-JsonPath', $JsonPath) }
            if ($EnableMacros.IsPresent) { $args += '-EnableMacros' }
            return $args
        }
        'power-query' {
            Assert-Required -Value $WorkbookPath -Name 'WorkbookPath'
            Assert-Required -Value $PowerQueryAction -Name 'PowerQueryAction'
            Assert-Required -Value $QueryName -Name 'QueryName'

            $args = @(
                '-WorkbookPath', $WorkbookPath,
                '-Action', $PowerQueryAction,
                '-QueryName', $QueryName,
                '-TimeoutSeconds', [string]$TimeoutSeconds
            )

            if (-not [string]::IsNullOrWhiteSpace($MFormula)) { $args += @('-MFormula', $MFormula) }
            if (-not [string]::IsNullOrWhiteSpace($MFormulaPath)) { $args += @('-MFormulaPath', $MFormulaPath) }
            if (-not [string]::IsNullOrWhiteSpace($WorksheetName)) { $args += @('-WorksheetName', $WorksheetName) }
            if (-not [string]::IsNullOrWhiteSpace($StartCell)) { $args += @('-StartCell', $StartCell) }
            if (-not [string]::IsNullOrWhiteSpace($LogPath)) { $args += @('-LogPath', $LogPath) }
            if (-not [string]::IsNullOrWhiteSpace($JsonPath)) { $args += @('-JsonPath', $JsonPath) }
            if ($EnableMacros.IsPresent) { $args += '-EnableMacros' }
            return $args
        }
        default {
            throw "Unsupported action: $Action"
        }
    }
}

try {
    $preflight = Get-OfficeComPreflightResult -Apps @('Excel')
    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $preflight -AppName 'Excel'

    if ($null -ne $failureInfo) {
        Write-ResultAndExit -Payload ([ordered]@{
                status = 'error'
                action = $Action
                error_kind = $failureInfo.error_kind
                message = $failureInfo.message
                preflight = $preflight
            }) -ExitCode 2
    }

    $child = Invoke-ChildPowerShellScript -ScriptPath (Get-ActionScript) -ScriptArguments (Get-ActionArguments)
    if ($child.exit_code -ne 0) {
        Write-ResultAndExit -Payload ([ordered]@{
                status = 'error'
                action = $Action
                error_kind = 'office_action_failed'
                message = "The underlying xlsx-win script failed for action '$Action'."
                preflight = $preflight
                tool = $child
            }) -ExitCode $child.exit_code
    }

    Write-ResultAndExit -Payload ([ordered]@{
            status = 'success'
            action = $Action
            message = "xlsx-win action '$Action' completed successfully."
            preflight = $preflight
            tool = $child
        }) -ExitCode 0
}
catch {
    Write-ResultAndExit -Payload ([ordered]@{
            status = 'error'
            action = $Action
            error_kind = 'invalid_arguments'
            message = $_.Exception.Message
        }) -ExitCode 1
}
