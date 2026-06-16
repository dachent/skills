# PowerPoint COM Workflow

Use this workflow when PowerPoint desktop is installed locally.

## Why COM first

PowerPoint COM uses the same rendering and save engine that the user will open later in PowerPoint. That makes it the preferred path for:

- editing existing decks
- exporting slide PNGs or PDFs
- preserving notes and presentation features
- working with branded templates
- avoiding renderer mismatches from LibreOffice

## Standard sequence

1. Run the smoke test once on a new machine or repo checkout.
2. Inspect the package without COM using `inspect_metadata.py` and `check_text_overflow.py`.
3. Inspect the source deck with `presentation_report.ps1`.
4. Export slide images with `export_slides.ps1`.
5. Make the smallest edit that satisfies the task.
6. Save to a new output path.
7. Re-run static checks, re-export slides, and inspect again.
8. Re-open the saved file in read-only mode to verify it is healthy.

## Script selection

### Inspect
```bash
python scripts/inspect_metadata.py input.pptx --format markdown --output metadata.md
python scripts/check_text_overflow.py input.pptx --format markdown --output text-risk.md
powershell -ExecutionPolicy Bypass -File scripts/presentation_report.ps1 -InputPath input.pptx -OutputPath report.json -Format json
```

### Render
```bash
powershell -ExecutionPolicy Bypass -File scripts/export_slides.ps1 -InputPath input.pptx -OutputDir rendered
```

### Replace placeholder text
```bash
powershell -ExecutionPolicy Bypass -File scripts/replace_text.ps1 -InputPath template.pptx -OutputPath output.pptx -MapPath replacements.json
```

### Export PDF
```bash
powershell -ExecutionPolicy Bypass -File scripts/export_pdf.ps1 -InputPath output.pptx -OutputPath output.pdf
```

## Writing custom automation

Import the module:

```powershell
Import-Module "$PSScriptRoot/pptx_com.psm1" -Force
```

Typical structure:

```powershell
$app = $null
$presentation = $null
try {
    $app = New-PowerPointApplication
    $presentation = Open-PowerPointPresentation -App $app -Path "input.pptx" -ReadOnly:$false

    # edit slides here

    Save-PowerPointPresentation -Presentation $presentation -Path "output.pptx" | Out-Null
}
finally {
    Close-PowerPointPresentation -Presentation $presentation
    Stop-PowerPointApplication -App $app
}
```

## Object model guidance

- Work in points, not inches. `1 inch = 72 points`.
- Slides are 1-based in the COM collections.
- Text can live in regular text boxes, placeholders, grouped shapes, tables, and notes pages.
- Tables require walking rows and columns and editing each cell's shape text.
- Notes live under `Slide.NotesPage.Shapes`.

## Save and export formats

- `.pptx`: use `ppSaveAsOpenXMLPresentation` value `24`
- `.pdf`: use `ppSaveAsPDF` value `32`
- per-slide PNG or JPG: use `Presentation.Export` with `PNG` or `JPG`

## Verification

Always do both:

- content verification from the saved file after reopening it
- visual verification from exported slide images

For no-template decks, also review `references/no-template-deck-design.md`, `references/slide-layout-patterns.md`, and `references/visual-qa-rubric.md` so the deck is judged against an explicit concept, reusable layout system, and screenshot repair rubric.
