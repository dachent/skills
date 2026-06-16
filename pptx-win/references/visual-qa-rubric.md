# Visual QA Rubric

Use this rubric after exporting slide screenshots. It closes the loop between automation and design judgment.

## What This Adds

The rubric gives Codex concrete visual checks for decks created without a template. It explains what to inspect, why the check matters, and what to repair.

## Required Screenshot Checks

For each rendered slide, inspect:

- Message clarity: the main point is visible within a few seconds.
- Hierarchy: title, key visual, evidence, and annotation have distinct visual roles.
- Alignment: edges, margins, and repeated objects line up consistently.
- Spacing: no cramped clusters, accidental gaps, or floating fragments.
- Text fit: no clipped text, tiny labels, or dense paragraphs masquerading as bullets.
- Contrast: foreground and background are readable, including chart labels and annotations.
- Palette discipline: accents guide attention rather than tinting everything.
- Asset quality: images, logos, screenshots, and icons are sharp and intentional.
- Chart/table readability: labels, legends, units, and takeaways are clear.
- Deck rhythm: repeated slide types feel related without becoming monotonous.

## Severity Levels

- Blocker: clipped text, unreadable contrast, missing asset, broken chart, corrupted export, or a slide whose message cannot be understood.
- Major: clutter, inconsistent alignment, overloaded table, unclear chart takeaway, or motif changes that make the deck feel accidental.
- Minor: small spacing inconsistencies, weak caption placement, or polish issues that do not block understanding.

## Repair Rules

- Fix blockers before adding new content.
- Reduce density before shrinking text.
- Move detail to speaker notes or appendix slides when the main slide is overloaded.
- Prefer one visual improvement with a clear purpose over several decorative additions.
- Re-export screenshots after repair; do not rely on the editable deck view alone.

## COM Boundary

The rubric can be applied in normal Codex execution if rendered screenshots already exist. Creating those screenshots from `.pptx` files requires PowerPoint COM through `scripts/export_slides.ps1` in a desktop-user/elevated session or the Office runner.
