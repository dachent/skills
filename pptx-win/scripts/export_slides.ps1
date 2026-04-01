[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$InputPath,
    [string]$OutputDir,
    [ValidateSet('PNG', 'JPG')] [string]$Format = 'PNG',
    [int]$Width = 1600,
    [int]$Height = 900,
    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'pptx_com.psm1') -Force -DisableNameChecking

$app = $null
$presentation = $null
try {
    $resolvedInput = Resolve-AbsolutePath -Path $InputPath
    if ([string]::IsNullOrWhiteSpace($OutputDir)) {
        $parent = Split-Path -Parent $resolvedInput
        $stem = [System.IO.Path]::GetFileNameWithoutExtension($resolvedInput)
        $OutputDir = Join-Path $parent ($stem + '-slides')
    }
    $resolvedOutput = Resolve-AbsolutePath -Path $OutputDir -AllowMissing

    $app = New-PowerPointApplication -Visible:$Visible.IsPresent
    $presentation = Open-PowerPointPresentation -App $app -Path $resolvedInput -ReadOnly:$true -WithWindow:$Visible.IsPresent
    $files = Export-PowerPointPresentationSlides -Presentation $presentation -OutputDir $resolvedOutput -FilterName $Format -Width $Width -Height $Height

    [pscustomobject]@{
        input_path = $resolvedInput
        output_dir = $resolvedOutput
        format = $Format
        slide_count = $presentation.Slides.Count
        files = @($files)
    } | ConvertTo-Json -Depth 4
}
finally {
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
