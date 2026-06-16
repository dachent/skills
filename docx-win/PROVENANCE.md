# Provenance

## Source

- Upstream repo or source document: `https://github.com/anthropics/skills`
- Upstream path: `skills/docx`
- Upstream commit/date: `57546260929473d4e0d1c1bb75297be2fdfa1949` / `2026-06-15`
- License reviewed: upstream `LICENSE.txt` is preserved in snapshots; redistribution policy requires separate review.

## Port Classification

- `port_depth`: `windows-com-adaptation`
- Verbatim copy: no
- Light adaptation: no
- Heavy adaptation: yes
- Original skill: no

## Design Upskill Contribution

Pinned provenance lets future `docx-win` design work explain which document-quality behavior comes from upstream guidance and which behavior is a Windows/Codex adaptation. That matters for no-template design because Word outputs need layout fidelity, real styles, comments, tracked changes, and PDF evidence instead of ad hoc XML edits or unreviewed formatting.

## COM Boundary

Documentation, static validation, and provenance checks can run in normal Codex execution. True Word COM operations such as opening documents, updating fields, exporting PDF, and validating repair-free round trips may need desktop-user or elevated PowerShell, or a self-hosted Office runner.

## Intentional Divergences

| Upstream behavior | Local behavior | Reason | Test coverage |
| --- | --- | --- | --- |
| General document skill behavior in `skills/docx` | Windows Word COM-first workflow in `docx-win` | Word desktop COM provides higher fidelity for pagination, fields, comments, tracked changes, and PDF export on Windows | `docx-win/scripts/smoke-test.ps1`; hosted syntax validation |
| Upstream implementation choices may use non-COM tooling | Local wrappers route COM work through shared preflight and desktop-user guidance | Codex sandbox sessions can be the wrong Windows logon context for Office COM | `.shared/office-com/scripts/office_com_preflight.ps1`; Office smoke workflow |
| Upstream guidance does not define a no-template Word design rubric | Local `references/document-quality-map.md` adds a document-quality behavior map for structure, styles, page system, review state, and PDF evidence | Codex needs explicit design judgment when there is no user template to copy | `tools/test_office_com_contract.py`; hosted reference validation |

## Last Alignment Review

- Reviewed date: 2026-06-16
- Reviewer: Codex Phase 3 Office runtime alignment pass
- Upstream commit compared: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Local commit reviewed: `74c04d0d16156e28f158d83aa38617e329cc1927`
- Result: document-quality behavior map added; non-COM documentation and static contract checks are separated from Word COM operations that may require desktop-user or elevated PowerShell.
