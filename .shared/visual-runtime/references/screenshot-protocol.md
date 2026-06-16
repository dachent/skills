# Screenshot protocol

Use this protocol whenever a skill or agent needs browser-rendered visual evidence.

## Viewports

Capture at least:

- desktop: `1440x900`
- mobile: `390x844`

Add tablet, print, or embedded-widget dimensions when the target artifact will be viewed in those contexts.

## Naming

Use stable, reviewable names:

- `desktop-home.png`
- `mobile-home.png`
- `desktop-dashboard-lint.json`
- `contact-sheet.html`

Avoid temporary names in final evidence. The filenames should explain what was rendered.

## Browser Evidence

For each capture set, preserve:

- screenshot PNG,
- `manifest.json`,
- `console-events.json`,
- `request-failures.json`,
- optional PDF when print or handoff fidelity matters.

## Inspection Notes

Every screenshot review should record:

- viewport,
- artifact URL or file path,
- major defects found,
- fixes made,
- residual risks or accepted tradeoffs.

## Why This Upskills Codex

Screenshots force Codex to confront the visual result. The protocol turns design review from a vague claim into a repeatable artifact trail: render, inspect, repair, and show evidence.
