---
name: theme-factory-codex
description: Use when Codex needs to create, adapt, audit, or repair a visual theme, design tokens, color palette, typography scale, spacing system, CSS variables, or brand-like styling for a no-template frontend, web artifact, dashboard, or visual deliverable.
---

# Theme Factory Codex

## Overview

Use this skill to create a restrained theme that can be reused across a visual artifact. Start with semantic design tokens before styling individual components.

## Design Upskill Contribution

This skill teaches Codex to make visual choices as a system. It improves no-template work by turning palette, typography, spacing, radius, and state colors into named decisions that can be checked in screenshots.

It matters because no-template design often fails through random color use, mismatched type, and one-off component styling. Tokens give Codex a memory for the artifact's visual language.

## Workflow

1. Identify audience, domain, tone, and existing brand constraints.
2. Define semantic design tokens for background, surface, text, muted text, border, accent, success, warning, danger, type, spacing, and radius.
3. Avoid one-note palettes dominated by a single hue family unless the domain requires it.
4. Check contrast before expanding the palette.
5. Apply tokens to core surfaces, controls, charts, and annotations.
6. Capture screenshots and revise tokens when the rendered theme feels cluttered, weak, or inconsistent.

## Shared Visual Runtime

Use `.shared\visual-runtime` for rendered theme checks:

- `capture_page.mjs` for before/after screenshots.
- `visual_lint.mjs` for contrast, tiny text, overflow, and console findings.
- the design-token guidance in the shared visual runtime references when token choices are unclear.

No Office COM is required. Office-specific theme embedding belongs to an Office skill after browser visual QA is complete.

## Verification

Before completion:

- inspect the token names and confirm they are semantic rather than arbitrary;
- capture screenshots at the target viewports;
- run visual lint and fix contrast or text-size blockers;
- compare palette, typography, and spacing across repeated components;
- preserve screenshot evidence showing the theme in use.

## Common Mistakes

- Picking colors one component at a time.
- Using decoration to compensate for weak hierarchy.
- Letting charts, buttons, and alerts use unrelated palettes.
- Claiming a theme works without seeing it rendered.
