---
name: pptx-win
description: windows powerpoint automation for .pptx files in codex app or other local windows environments with microsoft 365 installed. use when chatgpt needs to open, inspect, edit, create, render, export, or qa powerpoint presentations on windows, especially existing decks, template-based edits, speaker notes, slide images, pdf export, placeholder replacement, or smoke testing via native powerpoint com automation. prefer this skill over libreoffice-based flows when powerpoint desktop is available.
disable-model-invocation: true
---

# Pptx Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/pptx`
- Source branch: `main`

### Porting Notes

- This is a light Windows-specific port of Anthropic's `pptx` skill for Codex.
- The upstream skill centers on unpack/XML workflows, template editing guidance, and non-COM presentation tooling.
- This port changes the preferred execution path to PowerShell wrappers around Microsoft PowerPoint COM for inspection, export, placeholder replacement, rendering, and targeted edits, while preserving OOXML utilities as fallback tools.
- It remains Windows-only because the preferred workflow depends on a local Microsoft PowerPoint desktop installation and COM automation.

Use native Microsoft PowerPoint COM automation first.

Assume this skill runs in a local Windows environment with PowerPoint desktop installed through Microsoft 365. Prefer PowerShell and COM over LibreOffice for opening, editing, exporting, and rendering presentations.

## Workflow Decision Tree

1. **Need to confirm the environment works?**
   Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File pptx-win\scripts\smoke_test.ps1
   ```

2. **Need to inspect an existing deck?**
   Run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File pptx-win\scripts\presentation_report.ps1 -InputPath deck.pptx -OutputPath deck.report.json -Format json
   powershell -ExecutionPolicy Bypass -File pptx-win\scripts\export_slides.ps1 -InputPath deck.pptx -OutputDir rendered
   ```
   Use the JSON report for text, notes, and shape inventory. Use the exported slide images for visual QA.

3. **Need to update placeholder text or perform broad find/replace edits?**
   Create a JSON mapping file, then run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File pptx-win\scripts\replace_text.ps1 -InputPath template.pptx -OutputPath draft.pptx -MapPath replacements.json
   ```
   Use this first for template adaptation before writing a custom script.

4. **Need to create or heavily restructure slides?**
   Write a task-specific PowerShell script that imports `pptx-win\scripts\pptx_com.psm1` and uses PowerPoint COM directly. Use `pptx-win\scripts\smoke_test.ps1` as a working starter example.

5. **Need low-level OOXML surgery that COM cannot express safely?**
   Read `pptx-win\references\ooxml-fallback.md` and use the bundled Python utilities in `pptx-win\scripts\office\` plus `pptx-win\scripts\clean.py` and `pptx-win\scripts\add_slide.py`.
   If the Python imports are missing, install the bundled requirements first:
   ```powershell
   python -m pip install -r pptx-win\scripts\requirements.txt
   ```
   Only use this fallback when COM automation is insufficient or when the task explicitly requires XML-level manipulation.

## Quick Start

### Smoke test
```powershell
powershell -ExecutionPolicy Bypass -File pptx-win\scripts\smoke_test.ps1
```
This verifies that PowerPoint can be automated locally, that a presentation can be created and saved, and that PNG and PDF exports work.

### Inspect a deck
```powershell
powershell -ExecutionPolicy Bypass -File pptx-win\scripts\presentation_report.ps1 -InputPath input.pptx -OutputPath input.report.md -Format markdown
powershell -ExecutionPolicy Bypass -File pptx-win\scripts\export_slides.ps1 -InputPath input.pptx -OutputDir input-slides
```

### Replace placeholders
`replacements.json`
```json
{
  "{{CLIENT_NAME}}": "Contoso Fertility",
  "{{DATE}}": "2026-03-18"
}
```

```powershell
powershell -ExecutionPolicy Bypass -File pptx-win\scripts\replace_text.ps1 -InputPath template.pptx -OutputPath output.pptx -MapPath replacements.json
```

### Export PDF
```powershell
powershell -ExecutionPolicy Bypass -File pptx-win\scripts\export_pdf.ps1 -InputPath output.pptx -OutputPath output.pdf
```

## Operating Rules

- Open presentations with `WithWindow` disabled unless a visible window is required for debugging.
- Save edited output to a new path unless the user explicitly wants in-place edits.
- Close every presentation and quit the PowerPoint application in `finally` blocks. Release COM objects after use.
- Export slide images after every material change and inspect them before declaring success.
- Prefer PowerPoint's own PDF and image export over any alternate renderer.
- Treat modal dialogs, Protected View, missing fonts, and file locks as likely failure modes on Windows.
- Keep speaker notes and comments unless the user explicitly asks to remove them.

## Reading And Analysis Workflow

1. Generate a structured report with `pptx-win\scripts\presentation_report.ps1`.
2. Export slides to PNG with `pptx-win\scripts\export_slides.ps1`.
3. Review text, notes, titles, and hidden-slide status from the report.
4. Review visual layout from the PNGs.
5. If the task is text-only, avoid OOXML unpacking.

## Editing Workflow

1. Inspect the original deck with `presentation_report.ps1` and `export_slides.ps1`.
2. For placeholder replacement or text refreshes, use `replace_text.ps1` first.
3. For layout changes, write a targeted PowerShell script that imports `pptx_com.psm1` and edits only the needed slides and shapes.
4. Save to a new output file.
5. Re-export slides and inspect visually.
6. Re-open the saved file and confirm slide count, titles, and notes survived the edit.

## Creation Workflow

1. Start from an existing branded template whenever available.
2. If no template exists, create a new presentation with PowerPoint COM and add slides, text boxes, pictures, charts, and notes directly.
3. Use points for coordinates because the COM object model expects them.
4. Save early, then export PNGs and iterate.
5. Use the smoke test script as starter code for new COM-driven generators.

## QA Loop

After every non-trivial edit:

1. Export slide PNGs.
2. Inspect for overflow, overlap, alignment drift, missing assets, and low-contrast text.
3. Re-open the saved presentation in read-only mode.
4. Confirm slide count and titles.
5. Export PDF if the user needs a shareable review artifact.

Do not declare success until the output deck has been reopened successfully and the rendered PNGs have been checked.

## Resources

All scripts and references live under `pptx-win\` relative to the repository root.

- `references\powerpoint-com-workflow.md`: recommended COM-first workflow and script usage.
- `references\troubleshooting.md`: common Windows and Office failure modes.
- `references\ooxml-fallback.md`: when and how to drop to OOXML utilities.
- `scripts\pptx_com.psm1`: shared COM helper functions.
- `scripts\smoke_test.ps1`: local environment verification and starter example.
- `scripts\presentation_report.ps1`: report titles, text, notes, and optional shape inventory.
- `scripts\export_slides.ps1`: render a deck to per-slide PNG or JPG files.
- `scripts\export_pdf.ps1`: export a deck to PDF with PowerPoint.
- `scripts\replace_text.ps1`: apply literal replacements across slides, tables, and notes.
- `scripts\office\`: bundled OOXML unpack, pack, and validation utilities retained as fallback.
