[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$InputPath,
    [string]$OutputPath,
    [ValidateSet('json', 'markdown')] [string]$Format = 'json',
    [switch]$IncludeShapeInventory,
    [switch]$ExcludeNotes,
    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'pptx_com.psm1') -Force -DisableNameChecking

$app = $null
$presentation = $null
try {
    $resolvedInput = Resolve-AbsolutePath -Path $InputPath
    $app = New-PowerPointApplication -Visible:$Visible.IsPresent
    $presentation = Open-PowerPointPresentation -App $app -Path $resolvedInput -ReadOnly:$true -WithWindow:$Visible.IsPresent

    $report = Get-PowerPointPresentationReport -Presentation $presentation -IncludeNotes:(-not $ExcludeNotes.IsPresent) -IncludeShapeInventory:$IncludeShapeInventory.IsPresent -SourcePath $resolvedInput
    if ($Format -eq 'markdown') {
        $content = Convert-PresentationReportToMarkdown -Report $report
    } else {
        $content = $report | ConvertTo-Json -Depth 10
    }

    if (-not [string]::IsNullOrWhiteSpace($OutputPath)) {
        $resolvedOutput = Resolve-AbsolutePath -Path $OutputPath -AllowMissing
        $parent = Split-Path -Parent $resolvedOutput
        if (-not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Set-Content -LiteralPath $resolvedOutput -Value $content -Encoding UTF8
    }

    $content
}
finally {
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
