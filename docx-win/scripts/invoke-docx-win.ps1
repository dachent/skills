[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('smoke-test', 'export-pdf', 'convert-doc-to-docx', 'accept-revisions', 'find-replace', 'add-comment')]
    [string]$Action,

    [string]$InputPath,
    [string]$OutputPath,
    [string]$WorkingDirectory,
    [string]$FindText,
    [string]$ReplaceText,
    [bool]$MatchCase = $false,
    [int]$Start,
    [int]$End,
    [string]$CommentText,
    [string]$Author = 'Codex',
    [string]$Initials = 'CX'
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
        'smoke-test' { return (Join-Path $PSScriptRoot 'smoke-test.ps1') }
        'export-pdf' { return (Join-Path $PSScriptRoot 'export-pdf.ps1') }
        'convert-doc-to-docx' { return (Join-Path $PSScriptRoot 'convert-doc-to-docx.ps1') }
        'accept-revisions' { return (Join-Path $PSScriptRoot 'accept-revisions.ps1') }
        'find-replace' { return (Join-Path $PSScriptRoot 'find-replace.ps1') }
        'add-comment' { return (Join-Path $PSScriptRoot 'add-comment.ps1') }
        default { throw "Unsupported action: $Action" }
    }
}

function Get-ActionArguments {
    switch ($Action) {
        'smoke-test' {
            $args = @()
            if (-not [string]::IsNullOrWhiteSpace($WorkingDirectory)) { $args += @('-WorkingDirectory', $WorkingDirectory) }
            return $args
        }
        'export-pdf' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            return @('-InputPath', $InputPath, '-OutputPath', $OutputPath)
        }
        'convert-doc-to-docx' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            return @('-InputPath', $InputPath, '-OutputPath', $OutputPath)
        }
        'accept-revisions' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            return @('-InputPath', $InputPath, '-OutputPath', $OutputPath)
        }
        'find-replace' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $FindText -Name 'FindText'
            Assert-Required -Value $ReplaceText -Name 'ReplaceText'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            $args = @('-InputPath', $InputPath, '-FindText', $FindText, '-ReplaceText', $ReplaceText, '-OutputPath', $OutputPath)
            if ($MatchCase) {
                $args += '-MatchCase:$true'
            }
            return $args
        }
        'add-comment' {
            Assert-Required -Value $InputPath -Name 'InputPath'
            Assert-Required -Value $CommentText -Name 'CommentText'
            Assert-Required -Value $OutputPath -Name 'OutputPath'
            return @(
                '-InputPath', $InputPath,
                '-Start', [string]$Start,
                '-End', [string]$End,
                '-CommentText', $CommentText,
                '-Author', $Author,
                '-Initials', $Initials,
                '-OutputPath', $OutputPath
            )
        }
        default {
            throw "Unsupported action: $Action"
        }
    }
}

try {
    $preflight = Get-OfficeComPreflightResult -Apps @('Word')
    $failureInfo = Get-OfficePreflightFailureInfo -Preflight $preflight -AppName 'Word'

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
                message = "The underlying docx-win script failed for action '$Action'."
                preflight = $preflight
                tool = $child
            }) -ExitCode $child.exit_code
    }

    Write-ResultAndExit -Payload ([ordered]@{
            status = 'success'
            action = $Action
            message = "docx-win action '$Action' completed successfully."
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
