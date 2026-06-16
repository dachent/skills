---
name: artifact-runtime-codex
description: Use when Codex needs to run, package, validate, hand off, or debug the runtime for a browser visual artifact, including local server setup, asset paths, evidence bundles, screenshot review artifacts, or no-template visual QA handoff.
---

# Artifact Runtime Codex

## Overview

Use this skill when the main risk is not the design idea but whether the artifact runs, loads assets, and carries enough evidence for another person or agent to review it.

## Design Upskill Contribution

This skill teaches Codex to preserve runtime handoff evidence. It improves no-template work by making the local server, asset paths, screenshot outputs, console capture, visual lint, and evidence bundle part of the deliverable contract.

It matters because visual artifacts often fail at the handoff boundary: they depend on a hidden dev server, miss assets, or lack evidence showing what was actually reviewed.

## Workflow

1. Identify how the artifact should run: file open, local server, dev server, static export, or hosted package.
2. Prefer the simplest runtime that matches the artifact's real constraints.
3. Verify asset paths, environment variables, generated files, and build outputs.
4. Capture evidence from the same runtime path the reviewer will use.
5. Package screenshots, lint output, console/request logs, PDFs, contact sheets, and a short handoff note.
6. Keep generated evidence out of source control unless the project explicitly wants fixture artifacts committed.

## Shared Visual Runtime

Use `.shared\visual-runtime` for runtime evidence:

- `capture_page.mjs` for local server or file-based screenshot capture.
- `visual_lint.mjs` for browser and layout defects.
- `export_pdf.mjs` for print or review handoff.
- `make_contact_sheet.py` for an evidence bundle contact sheet.

No Office COM is required. The Office COM validator can review Office logs later, but this skill only packages browser runtime evidence.

## Verification

Before completion:

- run the local server or file-open path that the user will use;
- capture screenshots from that exact runtime;
- inspect console and request failures;
- run visual lint;
- assemble an evidence bundle with stable filenames;
- document how to rerun the runtime handoff.

## Common Mistakes

- Giving a localhost URL without confirming the server is still running.
- Capturing screenshots from a different build than the handoff package.
- Forgetting generated assets or relative paths.
- Treating the evidence bundle as separate from the deliverable.
