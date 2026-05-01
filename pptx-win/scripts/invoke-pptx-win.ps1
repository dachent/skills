[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('smoke-test', 'report', 'export-slides', 'export-pdf', 'replace-text')]
    [string]$Action,

    [string]$InputPath,
    [string]$OutputPath,
    [string]$OutputDir,
    [string]$MapPath,
    [ValidateSet('json', 'markdown', 'PNG', 'JPG')]
    [string]$Format,
    [int]$Width = 1600,
    [int]$Height = 900,
    [switch]$IncludeShapeInventory,
    [switch]$ExcludeNotes,
    [switch]$Visible
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
        'smoke-test' { return (Join-Path $PSScriptRoot 'smoke_test.ps1') }
        'report' { return (Join-Path $PSScriptRoot 'presentation_report.ps1') }
        'export-slides' { return (Join-Path $PSScriptRoot 'export_slides.ps1') }
        'export-pdf' { return (Join-Path $PSScriptRoot 'export_pdf.ps1') }
        'replace-text' { return (Join-Path $PSScriptRoot 'replace_text.ps1') }
        default { throw "Unsupported action: $Action" }
    }
}

function Get-ActionArguments {
    switch ($Action) {
        'smoke-test' {
            $args = @()
            if (-not [string]::IsNullOrWhiteSpace($OutputDir)) { $args += @('-OutputDir', $OutputDir) }
            if ($Visible.IsPresent) { $args += '-Visible' }
            return $args
        }
        'report' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            $args = @('-InputPath', $InputPath)
            if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $args += @('-OutputPath', $OutputPath) }
            if (-not [string]::IsNullOrWhiteSpace($Format)) { $args += @('-Format', $Format) }
            if ($IncludeShapeInventory.IsPresent) { $args += '-IncludeShapeInventory' }
            if ($ExcludeNotes.IsPresent) { $args += '-ExcludeNotes' }
            if ($Visible.IsPresent) { $args += '-Visible' }
            return $args
        }
        'export-slides' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            $args = @('-InputPath', $InputPath, '-Width', [string]$Width, '-Height', [string]$Height)
            if (-not [string]::IsNullOrWhiteSpace($OutputDir)) { $args += @('-OutputDir', $OutputDir) }
            if (-not [string]::IsNullOrWhiteSpace($Format)) { $args += @('-Format', $Format) }
            if ($Visible.IsPresent) { $args += '-Visible' }
            return $args
        }
        'export-pdf' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            $args = @('-InputPath', $InputPath)
            if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $args += @('-OutputPath', $OutputPath) }
            if ($Visible.IsPresent) { $args += '-Visible' }
            return $args
        }
        'replace-text' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            Assert-Required -Value $MapPath -Name 'MapPath'
            $args = @('-InputPath', $InputPath, '-OutputPath', $OutputPath, '-MapPath', $MapPath)
            if ($ExcludeNotes.IsPresent) { $args += '-ExcludeNotes' }
            if ($Visible.IsPresent) { $args += '-Visible' }
            return $args
        }
        default {
            throw "Unsupported action: $Action"
        }
    }
}

try {
    $preflight = Get-OfficeComPreflightResult -Apps @('PowerPoint')
    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $preflight -AppName 'PowerPoint'

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
                message = "The underlying pptx-win script failed for action '$Action'."
                preflight = $preflight
                tool = $child
            }) -ExitCode $child.exit_code
    }

    Write-ResultAndExit -Payload ([ordered]@{
            status = 'success'
            action = $Action
            message = "pptx-win action '$Action' completed successfully."
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
