[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$InputPath,
    [Parameter(Mandatory)] [string]$OutputPath,
    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'pptx_com.psm1') -Force -DisableNameChecking

$app = $null
$presentation = $null
try {
    $resolvedInput = Resolve-AbsolutePath -Path $InputPath
    $resolvedOutput = Resolve-AbsolutePath -Path $OutputPath -AllowMissing

    $app = New-PowerPointApplication -Visible:$Visible.IsPresent
    $presentation = Open-PowerPointPresentation -App $app -Path $resolvedInput -ReadOnly:$true -WithWindow:$Visible.IsPresent
    $saved = Save-PowerPointPresentation -Presentation $presentation -Path $resolvedOutput -FileFormat 32

    [pscustomobject]@{
        input_path = $resolvedInput
        output_path = $saved
    } | ConvertTo-Json -Depth 3
}
finally {
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
