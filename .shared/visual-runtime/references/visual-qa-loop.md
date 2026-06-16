# Visual QA loop

Use this loop for web pages, HTML artifacts, dashboards, generated reports, canvas outputs, and other browser-rendered visual work.

## Loop

1. Capture screenshots for the important viewports.
2. Capture console events and request failures.
3. Run visual lint for obvious mechanical defects.
4. Inspect screenshots using the artifact's real audience and task.
5. Revise the source.
6. Capture again and preserve before/after evidence.

## What Codex Should Learn

When there is no template, Codex needs feedback from the rendered artifact. The loop teaches Codex to treat screenshots, PDFs, and lint output as design evidence. A visual decision is not finished until the output has been inspected at the relevant viewport and any material defect has either been fixed or deliberately accepted.

## Required Checks

- Layout: no clipped controls, accidental overlap, broken spacing, or confusing visual hierarchy.
- Content: labels, units, titles, captions, and calls to action are readable and specific.
- Responsiveness: important views work at desktop and mobile sizes.
- Console: runtime errors are absent or explained.
- Assets: images and media load at usable dimensions.
- Evidence: saved screenshots and lint reports are named so another reviewer can retrace the decision.

## Non-COM Boundary

This loop uses browser and image tooling only. Do not instantiate Word, PowerPoint, or Excel here. If the final artifact is later placed into an Office file, run that Office step through the Office COM workflow after browser visual QA is complete.
