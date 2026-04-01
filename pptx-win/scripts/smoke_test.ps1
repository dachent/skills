[CmdletBinding()]
param(
    [string]$OutputDir = ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), 'pptx-win', 'smoke-test-output')),
    [switch]$Visible
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'pptx_com.psm1') -Force -DisableNameChecking

$PP_LAYOUT_BLANK = 12
$MSO_TEXT_ORIENTATION_HORIZONTAL = 1

$app = $null
$presentation = $null
$reopened = $null
try {
    $resolvedOutputDir = Resolve-AbsolutePath -Path $OutputDir -AllowMissing
    if (-not (Test-Path -LiteralPath $resolvedOutputDir)) {
        New-Item -ItemType Directory -Path $resolvedOutputDir -Force | Out-Null
    }

    $pptxPath = Join-Path $resolvedOutputDir 'smoke-test.pptx'
    $pdfPath = Join-Path $resolvedOutputDir 'smoke-test.pdf'
    $slidesDir = Join-Path $resolvedOutputDir 'slides'

    $app = New-PowerPointApplication -Visible:$Visible.IsPresent
    $presentation = New-PowerPointPresentation -App $app -WithWindow:$Visible.IsPresent

    $slide = $presentation.Slides.Add(1, $PP_LAYOUT_BLANK)
    $title = $slide.Shapes.AddTextbox($MSO_TEXT_ORIENTATION_HORIZONTAL, 36, 24, 648, 54)
    $title.TextFrame.TextRange.Text = 'pptx-win smoke test'
    $title.TextFrame.TextRange.Font.Name = 'Aptos Display'
    $title.TextFrame.TextRange.Font.Size = 28
    $title.TextFrame.TextRange.Font.Bold = -1

    $body = $slide.Shapes.AddTextbox($MSO_TEXT_ORIENTATION_HORIZONTAL, 36, 96, 648, 180)
    $body.TextFrame.TextRange.Text = "created through powerpoint com automation`r`nrendered to png and pdf`r`nreopened for validation"
    $body.TextFrame.TextRange.Font.Name = 'Aptos'
    $body.TextFrame.TextRange.Font.Size = 18

    $noteShape = $slide.NotesPage.Shapes.AddTextbox($MSO_TEXT_ORIENTATION_HORIZONTAL, 36, 36, 500, 100)
    $noteShape.TextFrame.TextRange.Text = 'smoke-test-note'

    $savedPptx = Save-PowerPointPresentation -Presentation $presentation -Path $pptxPath -FileFormat 24
    $savedPdf = Save-PowerPointPresentation -Presentation $presentation -Path $pdfPath -FileFormat 32
    $exportedSlides = Export-PowerPointPresentationSlides -Presentation $presentation -OutputDir $slidesDir -FilterName 'PNG' -Width 1600 -Height 900

    if (-not (Test-Path -LiteralPath $savedPptx)) { throw 'PPTX output was not created.' }
    if (-not (Test-Path -LiteralPath $savedPdf)) { throw 'PDF output was not created.' }
    if (@($exportedSlides).Count -lt 1) { throw 'Slide PNG export failed.' }

    Close-PowerPointPresentation -Presentation $presentation
    $presentation = $null

    $reopened = Open-PowerPointPresentation -App $app -Path $savedPptx -ReadOnly:$true -WithWindow:$false
    $report = Get-PowerPointPresentationReport -Presentation $reopened -IncludeNotes:$true -IncludeShapeInventory:$false -SourcePath $savedPptx

    if ($report.slide_count -ne 1) { throw "Unexpected slide count after reopen: $($report.slide_count)" }
    if ($report.slides[0].title -ne 'pptx-win smoke test') { throw 'Unexpected title after reopen.' }
    if ($report.slides[0].notes -notcontains 'smoke-test-note') { throw 'Speaker notes were not preserved.' }

    [pscustomobject]@{
        passed = $true
        output_dir = $resolvedOutputDir
        pptx_path = $savedPptx
        pdf_path = $savedPdf
        slide_images = @($exportedSlides)
        slide_count = $report.slide_count
        title = $report.slides[0].title
        notes = @($report.slides[0].notes)
    } | ConvertTo-Json -Depth 6
}
finally {
    Close-PowerPointPresentation -Presentation $reopened
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
