# Render And Inspect Guidance

PowerPoint package inspection and screenshot inspection answer different questions. Use both for no-template design work.

## Non-COM Inspection

Run these in normal Codex execution:

```powershell
python .\pptx-win\scripts\inspect_metadata.py .\deck.pptx --format markdown --output .\deck.metadata.md
python .\pptx-win\scripts\check_text_overflow.py .\deck.pptx --format markdown --output .\deck.text-risk.md
```

These scripts inspect the `.pptx` package without launching PowerPoint. They are useful for slide size, counts, relationship inventory, media/chart/table presence, speaker-note presence, and text-density risk.

## COM Inspection

Run these only from a COM-capable desktop-user/elevated PowerShell session or the Office runner:

```powershell
powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\presentation_report.ps1 -InputPath .\deck.pptx -OutputPath .\deck.report.json -Format json -IncludeShapeInventory
powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\export_slides.ps1 -InputPath .\deck.pptx -OutputDir .\deck-rendered
powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\export_pdf.ps1 -InputPath .\deck.pptx -OutputPath .\deck.pdf
```

COM inspection is required for true rendering, real text bounds, font substitution, animation-adjacent behavior, and PowerPoint's own repair/open state.

## How To Combine Results

- If static metadata says a deck has dense text or many images, expect screenshot review to need more attention.
- If screenshot review shows overflow but static checks do not, trust the screenshot and PowerPoint COM report.
- If static checks show risk but screenshots look clean, mention that the risk was reviewed and cleared visually.
- If COM fails with wrong-session or access errors, preserve the static reports and rerun only the COM steps from the right Windows session.
