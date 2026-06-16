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

Phase 2 adds that visual-design layer to `pptx-win`: no-template deck creation guidance, slide layout patterns, screenshot QA criteria, render/inspect guidance, non-COM metadata inspection, static text-density risk checks, and fixture briefs for agent rehearsal. This teaches Codex to treat a deck as a designed artifact with a repair loop, not merely a valid `.pptx` package.

## COM Boundary

Documentation, static validation, fixtures, and provenance checks can run in normal Codex execution. True PowerPoint COM operations such as opening decks, exporting PNG/PDF, inspecting live shapes, and detecting true text bounds may need desktop-user or elevated PowerShell, or a self-hosted Office runner.

## Intentional Divergences

| Upstream behavior | Local behavior | Reason | Test coverage |
| --- | --- | --- | --- |
| General presentation skill behavior in `skills/pptx` | Windows PowerPoint COM-first workflow in `pptx-win` | PowerPoint desktop COM provides higher fidelity for native deck inspection, rendering, image export, PDF export, notes, and shape edits | `pptx-win/scripts/smoke_test.ps1`; hosted syntax validation |
| Upstream implementation choices may use non-COM tooling | Local wrappers route COM work through shared preflight and desktop-user guidance | Codex sandbox sessions can be the wrong Windows logon context for Office COM | `.shared/office-com/scripts/office_com_preflight.ps1`; Office smoke workflow |
| Upstream guidance emphasizes presentation construction and package workflows | Local guidance now adds no-template visual concepting, reusable layout patterns, screenshot QA, and static deck risk reports | Codex needs explicit design judgment and rendered-evidence loops when there is no source template to imitate | `pptx-win/references/no-template-deck-design.md`; `pptx-win/references/visual-qa-rubric.md`; `pptx-win/scripts/inspect_metadata.py`; `pptx-win/scripts/check_text_overflow.py` |

## Last Alignment Review

- Reviewed date: 2026-06-16
- Reviewer: Codex Phase 2 visual alignment pass
- Upstream commit compared: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Local commit reviewed: `20f16d7887ba7d75eb58fe58063dc1dd6b95cc78`
- Result: provenance pinned; no-template visual design guidance and non-COM static inspection helpers added. True render/text-bound verification still requires PowerPoint COM from a desktop-user/elevated session or Office runner.
