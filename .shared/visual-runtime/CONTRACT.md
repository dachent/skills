# Shared Visual Runtime Contract

`.shared/visual-runtime` is the shared browser and image evidence layer for Codex no-template visual design work. It is intentionally separate from Office COM automation.

## Purpose

No-template design work needs a repeatable feedback loop:

1. render the artifact in a real browser,
2. inspect screenshots, console output, and exported PDFs,
3. detect layout, accessibility, and asset defects,
4. revise the source,
5. preserve evidence for review.

This runtime gives future visual skills a common way to create and check that evidence instead of inventing a new screenshot or visual-lint workflow in every skill.

## Design Upskill Contribution

The runtime teaches Codex to judge visual work from rendered output, not only from source code. It makes the design loop concrete: capture a viewport, record browser errors, flag obvious layout/accessibility risks, inspect image dimensions, assemble review sheets, and keep artifacts that reviewers can compare after revision.

That matters when there is no template because Codex has to learn from the artifact it produced. Screenshots, PDF exports, contact sheets, and machine-readable lint findings turn subjective polish into inspectable evidence.

## Runtime Boundary

This runtime is browser and image tooling only.

- No Office COM is required.
- No Word, PowerPoint, or Excel process should be created here.
- Office embedding, Office PDF export, PowerPoint slide rendering, Word pagination, and Excel refresh remain the responsibility of `.shared/office-com` and the Office skills.
- If a visual artifact later needs to be embedded into Word, PowerPoint, or Excel, do the browser/image work here first and move only the Office-specific export or validation step to a COM-capable session.

## Tools

- `scripts/capture_page.mjs`: render a URL or local HTML file with Playwright, capture a screenshot, console events, request failures, and an optional PDF.
- `scripts/export_pdf.mjs`: export a URL or local HTML file to PDF with Playwright.
- `scripts/visual_lint.mjs`: render a page and emit JSON findings for console errors, text overflow, low contrast, tiny text, and missing image metadata.
- `scripts/image_bounds.py`: inspect PNG, JPEG, and GIF image dimensions without external Python dependencies.
- `scripts/make_contact_sheet.py`: create an HTML contact sheet from screenshot or asset images.

## Evidence Artifacts

Runtime consumers should preserve:

- screenshots for each important viewport,
- `console-events.json` and `request-failures.json`,
- `visual-lint.json`,
- exported PDFs when print or handoff fidelity matters,
- contact sheets for multi-image or multi-viewport review,
- a short note explaining which findings were fixed, accepted, or deferred.

## Validation

Hosted validation should run without launching Office:

- Python contract checks in `tools/test_visual_runtime_contract.py`,
- `npm ci --ignore-scripts` in `.shared/visual-runtime`,
- `npm run check` to syntax-check JavaScript and compile Python,
- normal repository validation and provenance checks.

Playwright browser installation and live screenshot capture are runtime operations. They may require normal network access for browser downloads, but they do not require elevated PowerShell or Office COM.
