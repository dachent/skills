---
name: frontend-design-codex
description: Use when Codex is building, revising, or reviewing a frontend UI, web app screen, responsive layout, component surface, dashboard view, form flow, or no-template product interface that needs visual polish, accessibility, screenshots, or browser QA.
---

# Frontend Design Codex

## Overview

Use this skill to make browser-rendered product interfaces feel intentional, usable, and verified. Prefer the existing app framework and design conventions before adding new abstractions.

## Design Upskill Contribution

This skill teaches Codex to judge frontend design from rendered behavior rather than source code alone. It improves no-template work by forcing the agent to choose layout, hierarchy, spacing, controls, responsive states, accessibility, and screenshot evidence as one loop.

It matters because product UI without a template can easily become decorative or inconsistent. Codex should make useful interfaces that hold up under repeated use, mobile wrapping, and real browser rendering.

## Workflow

1. Inspect the existing app structure, framework, routes, components, styles, and design conventions.
2. Identify the primary user workflow and optimize the first screen for that workflow.
3. Build the smallest complete UI that covers normal, empty, loading, error, and narrow viewport states.
4. Use familiar controls: icon buttons for tools, toggles for binary choices, sliders or inputs for numbers, tabs for alternate views, and menus for option sets.
5. Keep typography and layout scaled to the surface. Avoid hero-scale text inside compact panels.
6. Capture desktop and mobile screenshots before claiming visual quality.
7. Revise until screenshot evidence supports the design decisions.

## Shared Visual Runtime

Use `.shared\visual-runtime` for browser evidence:

- `capture_page.mjs` for screenshots, console capture, request failures, and optional PDF export.
- `visual_lint.mjs` for text overflow, low contrast, tiny text, missing image alt text, and console findings.
- `make_contact_sheet.py` when comparing multiple screenshots.

No Office COM is required. If this UI is later exported into PowerPoint, Word, or Excel, finish browser QA first and move the Office-specific step to the Office skills.

## Verification

Before completion:

- run the app's normal build/test/lint command when available;
- capture at least desktop and mobile screenshots;
- run visual lint and address blockers;
- inspect screenshots for responsive UI, accessibility, hierarchy, text fit, controls, and spacing;
- preserve screenshot evidence and note any accepted tradeoffs.

## Common Mistakes

- Building a landing page when the user asked for a usable app.
- Inventing a visual language that conflicts with the existing app.
- Shrinking text to fix density instead of reducing content.
- Claiming responsive quality without a mobile screenshot.
