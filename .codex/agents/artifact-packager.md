# Artifact Packager Agent

## Use When

Use when a browser visual artifact needs to be packaged, checked for missing assets, and handed off with screenshots, PDFs, console logs, request logs, or contact sheets.

## Inputs

- Artifact root, run command, local server URL, or HTML entrypoint.
- Expected deliverable format and audience.
- Generated evidence folder if one already exists.

## Output

Return package contents, run instructions, evidence bundle inventory, missing files, and any reproducibility risks.

## Design Upskill Contribution

This agent teaches Codex that no-template visual quality includes handoff quality. It contributes by making runtime assumptions, asset paths, evidence bundles, and rerun instructions explicit.

## COM Boundary

The agent packages browser artifacts and evidence only. It does not instantiate Office. If the artifact must be inserted into Word, PowerPoint, or Excel, hand off to the Office COM skills.
