---
name: web-artifacts-builder-codex
description: Use when Codex needs to create, package, revise, or verify a standalone web artifact such as an HTML report, dashboard, microsite, interactive explainer, data story, or browser-delivered deliverable with screenshots, console capture, and evidence packaging.
---

# Web Artifacts Builder Codex

## Overview

Use this skill to build standalone web artifacts that open cleanly, explain themselves through the interface, and ship with enough evidence for another reviewer to trust the result.

## Design Upskill Contribution

This skill teaches Codex to treat web artifacts as deliverables, not just files. It improves no-template design by pairing layout and interaction choices with package evidence: screenshot captures, console capture, request failures, PDF export when useful, and a concise evidence bundle.

It matters because standalone artifacts often lack the guardrails of an existing app. The artifact must carry its own hierarchy, navigation, source notes, and failure evidence.

## Workflow

1. Define the artifact type: report, dashboard, explainer, portal, tracker, or prototype.
2. Choose the lightest implementation that can be opened and reviewed reliably.
3. Keep the first screen as the actual artifact experience, not a marketing page.
4. Make data/source limitations visible in the artifact when they affect interpretation.
5. Use stable file names and relative asset paths so the artifact can move as a folder.
6. Capture screenshots, console output, request failures, and optional PDF output.
7. Package the artifact with evidence and a short verification note.

## Shared Visual Runtime

Use `.shared\visual-runtime` for artifact verification:

- `capture_page.mjs` to render local HTML or a localhost URL and capture screenshots.
- `export_pdf.mjs` when the artifact needs print or handoff fidelity.
- `visual_lint.mjs` for obvious visual and console defects.
- `image_bounds.py` and `make_contact_sheet.py` for asset review and contact sheets.

No Office COM is required. If a standalone web artifact is later embedded into an Office file, that embedding/export step belongs to the relevant Office COM skill.

## Verification

Before completion:

- open or serve the standalone web artifact exactly as a reviewer would;
- verify relative assets load;
- run visual lint;
- preserve screenshot, manifest, console, request-failure, and optional PDF evidence;
- confirm the evidence bundle can be understood without hidden conversation context.

## Example Prompts

### HTML Memo And Dashboard

```text
Use $web-artifacts-builder-codex, $frontend-design-codex, $theme-factory-codex, and $artifact-runtime-codex.

Create a polished HTML memo and dashboard from the materials in:
[PASTE FOLDER OR FILE PATHS]

Objective:
Build an executive-ready HTML artifact that explains [TOPIC / DECISION / ANALYSIS] and includes both a written memo and an interactive dashboard.

Requirements:
- Do not use a template. Derive the visual system from the subject matter and source content.
- Include an executive summary, key findings, supporting analysis, risks/limitations, and recommended next steps.
- Include dashboard sections with KPI cards, charts, tables, filters or segmented views where useful.
- Make it responsive for desktop and mobile.
- Use the shared visual runtime for browser screenshots, PDF export, image bounds checks, and visual linting.
- Run accessibility and visual QA checks.
- Provide evidence artifacts: screenshots, PDF export, visual lint output, and a short QA note.
- Do not use Office COM unless exporting into an Office file becomes explicitly necessary.
- Save all outputs under: [OUTPUT FOLDER]
```

## Common Mistakes

- Shipping an artifact that only works from a dev server when the user needed a portable folder.
- Hiding caveats in conversation instead of the artifact or evidence note.
- Forgetting mobile or print views.
- Treating package evidence as optional.
