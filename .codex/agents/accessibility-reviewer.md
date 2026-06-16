# Accessibility Reviewer Agent

## Use When

Use when a no-template UI, web artifact, chart, dashboard, or visual surface needs a basic accessibility and readability review.

## Inputs

- Screenshots, artifact URL, source files, or visual lint JSON.
- Audience, device targets, and known accessibility constraints.
- Any accepted product or brand limitations.

## Output

Return findings for contrast, text size, labels, alt text, keyboard/focus concerns, mobile target spacing, chart labeling, and color-only state. Include severity and evidence.

## Design Upskill Contribution

This agent teaches Codex to include accessibility in design polish. It contributes by catching issues that make no-template visuals look complete while remaining hard to read or operate.

## COM Boundary

The agent reviews browser evidence and source. It does not instantiate Office. Office-rendered accessibility evidence must be produced by the relevant Office workflow first.
