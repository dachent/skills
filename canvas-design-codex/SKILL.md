---
name: canvas-design-codex
description: Use when Codex needs to build, revise, debug, or verify canvas, SVG, WebGL, Three.js, custom charting, diagram, game, generative visual, or pixel-based browser artwork where screenshot, pixel, animation, or image bounds evidence matters.
---

# Canvas Design Codex

## Overview

Use this skill for visual work where the primary output is drawn rather than ordinary DOM layout. Prefer proven rendering libraries for established rules, physics, charting, or 3D behavior.

## Design Upskill Contribution

This skill teaches Codex to verify drawn visuals through rendered pixels. It improves no-template design by requiring screenshot evidence, image bounds, animation sanity checks, and visual lint around the surrounding page.

It matters because canvas and SVG work can look correct in code while rendering blank, cropped, blurry, or misframed. Codex must prove that the pixels exist and communicate the intended design.

## Workflow

1. Identify the rendering mode: canvas, SVG, WebGL, Three.js, charting library, or mixed DOM and drawing.
2. Use existing libraries for established mechanics or 3D rendering instead of hand-rolling complex engines.
3. Set stable canvas or SVG dimensions with responsive constraints.
4. Add loading, error, empty, and reduced-motion behavior when relevant.
5. Capture screenshots and inspect image bounds after meaningful changes.
6. For animated or interactive work, verify the scene is nonblank and correctly framed after a short wait.

## Shared Visual Runtime

Use `.shared\visual-runtime` for visual evidence:

- `capture_page.mjs` with `--wait-ms` for animated or async drawing.
- `image_bounds.py` to confirm screenshot width, height, aspect ratio, and bytes.
- `make_contact_sheet.py` to compare states or viewports.
- `visual_lint.mjs` for surrounding DOM text, contrast, and console findings.

No Office COM is required. If drawn output is exported into an Office file later, keep the pixel evidence here and move only the Office embedding to the Office skill.

## Verification

Before completion:

- capture a screenshot after the canvas or visual has rendered;
- confirm image bounds and nonzero file size;
- inspect for crop, blur, blank canvas, offscreen objects, and overlapping UI;
- run visual lint for surrounding controls and labels;
- preserve screenshot or contact sheet evidence.

## Common Mistakes

- Verifying source code but not pixels.
- Allowing hover text, loading labels, or controls to resize the canvas.
- Using viewport-scaled type that breaks at narrow sizes.
- Forgetting to wait for async drawing before screenshot capture.
