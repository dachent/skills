# Provenance

## Source

- Upstream repo or source document: `https://github.com/anthropics/skills`
- Upstream path: `skills/pptx`
- Upstream commit/date: `57546260929473d4e0d1c1bb75297be2fdfa1949` / `2026-06-15`
- License reviewed: upstream `LICENSE.txt` is preserved in snapshots; redistribution policy requires separate review.

## Port Classification

- `port_depth`: `windows-com-adaptation`
- Verbatim copy: no
- Light adaptation: no
- Heavy adaptation: yes
- Original skill: no

## Design Upskill Contribution

Pinned provenance is the starting point for improving no-template deck design in Codex. It separates upstream slide-building guidance from the local PowerPoint COM fidelity path, so later visual-design changes can explain exactly what was adapted, why it helps Codex choose layouts, palettes, motifs, charts, and screenshot QA loops, and which local differences are intentional.

## COM Boundary

Documentation, static validation, fixtures, and provenance checks can run in normal Codex execution. True PowerPoint COM operations such as opening decks, exporting PNG/PDF, inspecting live shapes, and detecting true text bounds may need desktop-user or elevated PowerShell, or a self-hosted Office runner.

## Intentional Divergences

| Upstream behavior | Local behavior | Reason | Test coverage |
| --- | --- | --- | --- |
| General presentation skill behavior in `skills/pptx` | Windows PowerPoint COM-first workflow in `pptx-win` | PowerPoint desktop COM provides higher fidelity for native deck inspection, rendering, image export, PDF export, notes, and shape edits | `pptx-win/scripts/smoke_test.ps1`; hosted syntax validation |
| Upstream implementation choices may use non-COM tooling | Local wrappers route COM work through shared preflight and desktop-user guidance | Codex sandbox sessions can be the wrong Windows logon context for Office COM | `.shared/office-com/scripts/office_com_preflight.ps1`; Office smoke workflow |

## Last Alignment Review

- Reviewed date: 2026-06-15
- Reviewer: Codex Phase 1 provenance pass
- Upstream commit compared: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Local commit reviewed: `76567c666c081b92d652eee6f5ecff843c9fe1c4`
- Result: provenance pinned; screenshot-driven visual alignment requires follow-on review.
