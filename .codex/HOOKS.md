# Codex Hooks

This repository stores warning-only hook reminders for no-template design work. They are documentation-backed guardrails for Codex sessions and validators; they are not blocking policy.

## Why They Exist

The hooks make important review habits harder to skip:

- visual QA evidence before claiming browser or artifact design quality,
- PowerPoint rendering evidence or an explicit Office COM blocker,
- provenance review when skill behavior changes,
- Office COM boundary honesty,
- accessibility checks for no-template visual artifacts.

## Warning-Only Contract

Every hook in `.codex/hooks.json` must set `severity` to `warning` and `blocking` to `false`. A hook may remind Codex to run validation, but it must not prevent work from continuing or claim proof by itself.

## COM Boundary

No hook runs Office COM. Hooks may remind Codex to review PowerPoint rendering, Word/PDF export, Excel refresh, or COM logs, but actual Office automation still belongs in desktop-user/elevated PowerShell or the self-hosted Office runner.

## Design Upskill Contribution

The reminders keep Codex oriented toward evidence: screenshots, visual lint, accessibility review, PowerPoint rendering, provenance review, and explicit blockers. That helps no-template design work become inspectable rather than conversationally asserted.
