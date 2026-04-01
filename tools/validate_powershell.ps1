#requires -Version 7.0

[CmdletBinding()]
param(
    [string]$SettingsPath = '.github\PSScriptAnalyzerSettings.psd1'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-RepositoryRoot {
    $toolsRoot = Split-Path -Parent $PSScriptRoot
    return [System.IO.Path]::GetFullPath($toolsRoot)
}

function Format-Record {
    param(
        [Parameter(Mandatory)] [string]$File,
        [Parameter(Mandatory)] [int]$Line,
        [Parameter(Mandatory)] [string]$Message
    )

    return '{0}:{1}: {2}' -f $File, $Line, $Message
}

$repositoryRoot = Get-RepositoryRoot
$resolvedSettingsPath = [System.IO.Path]::GetFullPath((Join-Path $repositoryRoot $SettingsPath))

if (-not (Test-Path -LiteralPath $resolvedSettingsPath)) {
    throw "PSScriptAnalyzer settings file was not found: $resolvedSettingsPath"
}

if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
    throw 'PSScriptAnalyzer is not installed. Install the module before running this validation script.'
}

$powerShellFiles = Get-ChildItem -Path $repositoryRoot -Recurse -File |
    Where-Object { $_.Extension -in '.ps1', '.psm1' } |
    Sort-Object FullName

$parseFailures = New-Object System.Collections.Generic.List[string]
foreach ($file in $powerShellFiles) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null

    foreach ($parseError in $parseErrors) {
        $parseFailures.Add((Format-Record -File $file.FullName -Line $parseError.Extent.StartLineNumber -Message $parseError.Message))
    }
}

if ($parseFailures.Count -gt 0) {
    $message = @('PowerShell parse validation failed:') + $parseFailures
    throw ($message -join [Environment]::NewLine)
}

$analysisResults = @(
    Invoke-ScriptAnalyzer -Path $repositoryRoot -Recurse -Settings $resolvedSettingsPath |
        Sort-Object ScriptName, Line, RuleName
)

if ($analysisResults.Count -gt 0) {
    $formattedResults = foreach ($result in $analysisResults) {
        $line = if ($null -ne $result.Line) { [int]$result.Line } else { 0 }
        Format-Record -File $result.ScriptName -Line $line -Message ('[{0}] {1}' -f $result.RuleName, $result.Message)
    }

    $message = @('PSScriptAnalyzer reported issues:') + $formattedResults
    throw ($message -join [Environment]::NewLine)
}

Write-Output ('Validated {0} PowerShell files with parser and PSScriptAnalyzer.' -f $powerShellFiles.Count)
