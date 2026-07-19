---
name: pptx-win
description: windows powerpoint automation and no-template deck design support for .pptx files in codex app or other local windows environments with microsoft 365 installed. use when chatgpt needs to open, inspect, edit, create, render, export, or qa powerpoint presentations on windows, especially new decks without a template, existing deck edits, speaker notes, slide images, pdf export, placeholder replacement, visual QA, or smoke testing via native powerpoint com automation. prefer this skill over libreoffice-based flows when powerpoint desktop is available.
---

# Pptx Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/pptx`
- Source branch: `main`

### Porting Notes

- This is a Windows COM adaptation of Anthropic's `pptx` skill for Codex.
- The upstream skill centers on unpack/XML workflows, template editing guidance, and non-COM presentation tooling.
- This port changes the preferred execution path to PowerShell wrappers around Microsoft PowerPoint COM for inspection, export, placeholder replacement, rendering, and targeted edits, while preserving OOXML utilities as fallback tools.
- It adds no-template design guidance so Codex can choose layout systems, palettes, visual motifs, screenshot review criteria, and repair loops when a user does not provide a template.
- It remains Windows-only for high-fidelity rendering because the preferred workflow depends on a local Microsoft PowerPoint desktop installation and COM automation.

### Design Upskill Contribution

This skill now teaches Codex how to build and review decks when no template exists. The added guidance makes Codex name the deck job, choose a visual concept, reuse a small set of slide patterns, apply a restrained palette and type rhythm, run static package checks, export screenshots, and repair visible defects. This matters because no-template deck quality depends on design judgment plus rendered evidence, not only successful `.pptx` file creation.

Use native Microsoft PowerPoint COM automation first, but only after the helper preflight confirms the current shell is the signed-in desktop user session.

Assume this skill runs in a local Windows environment with PowerPoint desktop installed through Microsoft 365. Prefer PowerShell and COM over LibreOffice for opening, editing, exporting, and rendering presentations.

Before any PowerPoint COM step, run:

```powershell
& "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps PowerPoint
```

That path assumes a Codex-style install. If this skill is loaded through a Claude Code plugin instead, resolve the same script from the plugin cache first:

```powershell
$preflight = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache" -Recurse -Filter "office_com_preflight.ps1" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $preflight) { $preflight = "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" }
& $preflight -Apps PowerPoint
```

If preflight reports `can_use_com = false`, do not create `PowerPoint.Application` from the Codex sandbox. Prepare maps, output paths, and other non-COM inputs in Codex, then run the COM step from a regular PowerShell window opened as the signed-in desktop user.

## Workflow Decision Tree

1. **Need to confirm the environment works?**
   Run preflight first. If it passes, run:
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
   ```

2. **Need to create a deck without a template?**
   Read `references/no-template-deck-design.md`, choose layout patterns from `references/slide-layout-patterns.md`, and write down the concept, palette, type rhythm, and slide pattern set before creating slides. For static package checks after a draft exists, run:
   ```bash
   python scripts/inspect_metadata.py deck.pptx --format markdown --output deck.metadata.md
   python scripts/check_text_overflow.py deck.pptx --format markdown --output deck.text-risk.md
   ```
   Then export slide screenshots with PowerPoint COM and use `references/visual-qa-rubric.md` for the repair loop.

3. **Need to inspect an existing deck?**
   Run:
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts/presentation_report.ps1 -InputPath deck.pptx -OutputPath deck.report.json -Format json
   powershell -ExecutionPolicy Bypass -File scripts/export_slides.ps1 -InputPath deck.pptx -OutputDir rendered
   python scripts/inspect_metadata.py deck.pptx --format markdown --output deck.metadata.md
   python scripts/check_text_overflow.py deck.pptx --format markdown --output deck.text-risk.md
   ```
   Use the JSON report for text, notes, and shape inventory. Use the metadata and text-risk reports for non-COM review signals. Use the exported slide images for visual QA.

4. **Need to update placeholder text or perform broad find/replace edits?**
   Create a JSON mapping file, then run:
   ```bash
   powershell -ExecutionPolicy Bypass -File scripts/replace_text.ps1 -InputPath template.pptx -OutputPath draft.pptx -MapPath replacements.json
   ```
   Use this first for template adaptation before writing a custom script.

5. **Need to create or heavily restructure slides?**
   Write a task-specific PowerShell script that imports `scripts/pptx_com.psm1` and uses PowerPoint COM directly, but only from the desktop-user PowerShell window after preflight passes. Use `scripts/smoke_test.ps1` as a working starter example.

6. **Need low-level OOXML surgery that COM cannot express safely?**
   Read `references/ooxml-fallback.md` and use the bundled Python utilities in `scripts/office/` plus `scripts/clean.py` and `scripts/add_slide.py`.
   If the Python imports are missing, install the bundled requirements first:
   ```bash
   python -m pip install -r scripts/requirements.txt
   ```
   Only use this fallback when COM automation is insufficient or when the task explicitly requires XML-level manipulation.

## Quick Start

### Smoke test
```bash
powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1
```
This verifies that PowerPoint can be automated locally, that a presentation can be created and saved, and that PNG and PDF exports work.

From the skill-local desktop-user wrapper, the equivalent command is:

```powershell
& "$env:USERPROFILE\.codex\skills\pptx-win\scripts\invoke-pptx-win.ps1" -Action smoke-test -OutputDir .\ppt-smoke
```

### Inspect a deck
```bash
powershell -ExecutionPolicy Bypass -File scripts/presentation_report.ps1 -InputPath input.pptx -OutputPath input.report.md -Format markdown
powershell -ExecutionPolicy Bypass -File scripts/export_slides.ps1 -InputPath input.pptx -OutputDir input-slides
python scripts/inspect_metadata.py input.pptx --format markdown --output input.metadata.md
python scripts/check_text_overflow.py input.pptx --format markdown --output input.text-risk.md
```

### Replace placeholders
`replacements.json`
```json
{
  "{{CLIENT_NAME}}": "Contoso Fertility",
  "{{DATE}}": "2026-03-18"
}
```

```bash
powershell -ExecutionPolicy Bypass -File scripts/replace_text.ps1 -InputPath template.pptx -OutputPath output.pptx -MapPath replacements.json
```

### Export PDF
```bash
powershell -ExecutionPolicy Bypass -File scripts/export_pdf.ps1 -InputPath output.pptx -OutputPath output.pdf
```

## Operating Rules

- For a no-template deck, define the visual concept, palette, type rhythm, and reusable slide patterns before writing automation.
- Open presentations with `WithWindow` disabled unless a visible window is required for debugging.
- Save edited output to a new path unless the user explicitly wants in-place edits.
- Close every presentation and quit the PowerPoint application in `finally` blocks. Release COM objects after use.
- Never call `New-Object -ComObject PowerPoint.Application` directly from the Codex sandbox. Use the shared preflight and then run COM work from the signed-in desktop user session through `scripts/invoke-pptx-win.ps1` or a task-specific script.
- Export slide images after every material change and inspect them before declaring success.
- Treat `scripts/check_text_overflow.py` as a static risk signal only. True text bounds require PowerPoint COM rendering and screenshot inspection.
- Prefer PowerPoint's own PDF and image export over any alternate renderer.
- Treat modal dialogs, Protected View, missing fonts, and file locks as likely failure modes on Windows.
- Keep speaker notes and comments unless the user explicitly asks to remove them.

## Reading And Analysis Workflow

1. Generate non-COM package metadata with `scripts/inspect_metadata.py`.
2. Run static text-density risk checks with `scripts/check_text_overflow.py`.
3. Generate a COM structured report with `scripts/presentation_report.ps1` when PowerPoint COM is available.
4. Export slides to PNG with `scripts/export_slides.ps1`.
5. Review text, notes, titles, and hidden-slide status from the report.
6. Review visual layout from the PNGs with `references/visual-qa-rubric.md`.
7. If the task is text-only, avoid OOXML unpacking.

## Editing Workflow

1. Run the shared Office preflight in the desktop-user PowerShell window before any PowerPoint COM step.
2. Inspect the original deck with `presentation_report.ps1` and `export_slides.ps1`.
3. For placeholder replacement or text refreshes, use `replace_text.ps1` first.
4. For layout changes, write a targeted PowerShell script that imports `pptx_com.psm1` and edits only the needed slides and shapes.
5. If Codex is in the sandbox and preflight fails there, keep Codex on non-COM prep work and run the PowerPoint COM step from the desktop-user shell through `invoke-pptx-win.ps1` or the task-specific script.
6. Save to a new output file.
7. Re-export slides and inspect visually.
8. Re-open the saved file and confirm slide count, titles, and notes survived the edit.

## Creation Workflow

1. Start from an existing branded template whenever available.
2. If no template exists, read `references/no-template-deck-design.md` and select a visual concept, palette, type rhythm, and two or three patterns from `references/slide-layout-patterns.md`.
3. Create a new presentation with PowerPoint COM and add slides, text boxes, pictures, charts, and notes directly, but do it from the desktop-user PowerShell window after preflight succeeds.
4. Use points for coordinates because the COM object model expects them.
5. Save early, run the static metadata and text-risk scripts, then export PNGs and iterate.
6. Use the smoke test script as starter code for new COM-driven generators.

## QA Loop

After every non-trivial edit:

1. Run `scripts/inspect_metadata.py` to confirm package-level shape, media, chart, notes, and slide counts.
2. Run `scripts/check_text_overflow.py` to identify static text-density risk.
3. Export slide PNGs.
4. Inspect for message clarity, hierarchy, overflow, overlap, alignment drift, missing assets, chart readability, and low-contrast text using `references/visual-qa-rubric.md`.
5. Re-open the saved presentation in read-only mode.
6. Confirm slide count and titles.
7. Export PDF if the user needs a shareable review artifact.

Do not declare success until the output deck has been reopened successfully and the rendered PNGs have been checked.

If PowerPoint COM throws `0x80070520`, treat that as a wrong-session problem, not as a deck problem. Move the COM step to the signed-in desktop user session and rerun it there.

## Example Prompts

### Executive Presentation

```text
Use $pptx-win and $theme-factory-codex.

Create an executive PowerPoint presentation from:
[PASTE SOURCE FILES OR FOLDER]

Objective:
Build a polished presentation for [AUDIENCE] about [TOPIC / DECISION / RECOMMENDATION].

Requirements:
- Do not use a template unless one is provided. Create the design system from the content.
- Produce a clear narrative arc: context, problem, evidence, options, recommendation, next steps.
- Use strong slide hierarchy, concise titles, clean layouts, and chart-ready visuals.
- Include speaker notes where useful.
- Use PowerPoint COM for actual deck creation, rendering, PDF export, and validation.
- Run the Office COM preflight first. If COM is available, the agent should run the full smoke/validation path itself.
- Export slide PNGs and a PDF for QA.
- Inspect rendered slides for overflow, overlap, missing assets, and poor contrast before calling it done.
- Save the final `.pptx`, rendered PNGs, PDF, and QA notes under: [OUTPUT FOLDER]
```

## Resources

- `references/no-template-deck-design.md`: how to create and repair decks when no template exists.
- `references/slide-layout-patterns.md`: reusable patterns for no-template deck composition.
- `references/visual-qa-rubric.md`: screenshot inspection and repair criteria.
- `references/render-inspect-guidance.md`: how to combine non-COM package checks with COM render evidence.
- `references/powerpoint-com-workflow.md`: recommended COM-first workflow and script usage.
- `references/troubleshooting.md`: common Windows and Office failure modes.
- `references/ooxml-fallback.md`: when and how to drop to OOXML utilities.
- `scripts/pptx_com.psm1`: shared COM helper functions.
- `scripts/smoke_test.ps1`: local environment verification and starter example.
- `scripts/presentation_report.ps1`: report titles, text, notes, and optional shape inventory.
- `scripts/inspect_metadata.py`: non-COM `.pptx` package metadata report.
- `scripts/check_text_overflow.py`: non-COM static text-density risk checker. Use screenshots for final text-fit judgment.
- `scripts/export_slides.ps1`: render a deck to per-slide PNG or JPG files.
- `scripts/export_pdf.ps1`: export a deck to PDF with PowerPoint.
- `scripts/replace_text.ps1`: apply literal replacements across slides, tables, and notes.
- `scripts/office/`: bundled OOXML unpack, pack, and validation utilities retained as fallback.
