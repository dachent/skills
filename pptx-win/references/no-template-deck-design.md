# No-Template Deck Design

Use this reference when the user asks for a new deck and does not provide a template, brand book, or source deck to imitate.

## What This Adds

`pptx-win` now treats no-template deck work as a design workflow instead of only a PowerPoint automation task. The skill must choose a visual concept, create a small layout system, render screenshots, inspect those screenshots, and revise before declaring the deck ready.

## Why It Matters

Without a template, Codex has to make design decisions that a template normally carries: hierarchy, palette, rhythm, spacing, type scale, chart treatment, image treatment, and visual emphasis. This guidance upskills Codex by making those decisions explicit and reviewable instead of accidental.

## Default Design Process

1. Define the deck job: decision, update, pitch, training, workshop, board memo, or handoff.
2. Pick one visual concept that fits the audience and content. Examples: operating dashboard, clinical evidence memo, product narrative, investor update, research briefing.
3. Choose a restrained palette with one dark neutral, one light neutral, one primary accent, and one secondary accent. Avoid one-note palettes.
4. Establish a type rhythm: title, section label, body, annotation, chart label.
5. Choose two or three reusable slide patterns from `references/slide-layout-patterns.md`.
6. Build a complete draft with PowerPoint COM from a desktop-user/elevated PowerShell session if actual deck creation is needed.
7. Export slide PNGs and inspect them with `references/visual-qa-rubric.md`.
8. Repair the deck and re-export screenshots until the visible defects are resolved.

## Design Heuristics

- Put the slide's message in the title or the first visual group, not in a dense paragraph.
- Use fewer, stronger objects. A slide with six competing boxes is usually weaker than one composed visual and one annotation.
- Make hierarchy visible through size, weight, position, whitespace, and contrast before adding decorative color.
- Use consistent margins and alignment across the deck. A simple grid beats ad hoc positioning.
- Give charts a takeaway title, useful labels, and enough surrounding whitespace.
- Turn tables into structured comparison blocks when the audience needs to decide, not audit.
- Use real screenshots or generated visuals only when they clarify the subject; avoid atmospheric filler.
- Keep logos, dates, and footers quiet unless the task requires a formal title block.

## Screenshot Repair Loop

For no-template decks, screenshot review is the acceptance loop:

1. Export all slides with `scripts/export_slides.ps1`.
2. Create or inspect a visual contact sheet if available.
3. Review each slide against the rubric.
4. Run `scripts/inspect_metadata.py` and `scripts/check_text_overflow.py` for static risk signals.
5. Fix visual hierarchy, overflow, alignment, contrast, missing assets, and inconsistent motifs.
6. Re-export screenshots and compare against the prior pass.

## COM Boundary

Codex can write this design plan, inspect OOXML metadata, run static text-risk checks, and prepare automation scripts in normal execution. Actual PowerPoint open/save/render/export operations require a COM-capable desktop-user/elevated PowerShell session or the self-hosted Office runner when sandbox preflight fails.
