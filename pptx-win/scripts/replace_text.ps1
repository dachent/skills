[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$InputPath,
    [Parameter(Mandatory)] [string]$OutputPath,
    [Parameter(Mandatory)] [string]$MapPath,
    [switch]$ExcludeNotes,
    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'pptx_com.psm1') -Force -DisableNameChecking

$resolvedMapPath = Resolve-AbsolutePath -Path $MapPath
$mapping = Read-JsonFileAsHashtable -Path $resolvedMapPath
if ($mapping.Count -eq 0) {
    throw 'Replacement map is empty.'
}

$app = $null
$presentation = $null
try {
    $resolvedInput = Resolve-AbsolutePath -Path $InputPath
    $resolvedOutput = Resolve-AbsolutePath -Path $OutputPath -AllowMissing

    $app = New-PowerPointApplication -Visible:$Visible.IsPresent
    $presentation = Open-PowerPointPresentation -App $app -Path $resolvedInput -ReadOnly:$false -WithWindow:$Visible.IsPresent
    $changeCount = Replace-TextInPowerPointPresentation -Presentation $presentation -Map $mapping -IncludeNotes:(-not $ExcludeNotes.IsPresent)
    $saved = Save-PowerPointPresentation -Presentation $presentation -Path $resolvedOutput -FileFormat 24

    [pscustomobject]@{
        input_path = $resolvedInput
        output_path = $saved
        replacements_applied = $changeCount
        mapping_keys = @($mapping.Keys)
    } | ConvertTo-Json -Depth 5
}
finally {
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
