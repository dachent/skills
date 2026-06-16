# Word no-template document quality map

Use this map when `docx-win` has to create or materially reshape a polished Word deliverable without a user-provided template. It explains what Word-native behavior matters, why it improves design judgment, and how to verify it.

## Purpose

No-template document design is not just visual styling. A useful Word deliverable must survive editing, review, PDF export, and downstream reuse. Codex should make layout decisions through Word structures that carry meaning instead of only painting text to look right.

## Quality dimensions

| Dimension | What to do | Why it matters | Verification |
| --- | --- | --- | --- |
| Document structure | Use built-in or clearly named styles for title, headings, body text, captions, and lists. | Styles give the document a navigable hierarchy and make later global changes safe. | Open in Word, update fields, inspect the navigation pane or TOC, and confirm headings are not manual bold text. |
| Page system | Set margins, orientation, section breaks, headers, footers, and page numbers deliberately. | Page setup determines whether the design exports cleanly and reads professionally. | Compute page statistics, export PDF, and inspect page starts, widows, footers, and section transitions. |
| Tables | Build tables with Word table objects, header rows, consistent widths, and readable spacing. | Tables are where no-template docs most often fail because text wrapping and page breaks are renderer-dependent. | Export PDF and check wrapped cells, repeated headers, alignment, and page breaks. |
| Figures and charts | Insert images as inline shapes unless floating placement is required, set explicit dimensions, and keep captions near the visual. | Inline objects reduce accidental overlap and make PDF export more predictable. | Inspect the PDF at page boundaries and confirm each figure remains with its caption. |
| Review artifacts | Preserve or create comments and tracked changes only when the user asked for review markup. | Review state is part of the deliverable contract, not decoration. | Check revision count, comment count, and whether the final copy is clean or marked up as requested. |
| Field behavior | Update fields, page references, tables of contents, and cross-references before final save. | Word fields are dynamic; stale fields make an otherwise polished document untrustworthy. | Run field refresh, force repagination, save, and export again. |
| PDF evidence | Export a PDF companion for layout-sensitive work. | OOXML package inspection cannot prove final pagination or rendering. | Inspect exported pages or compare page counts after each meaningful layout change. |

## Default no-template choices

- Use a restrained typographic system: one body font, one heading scale, consistent spacing before and after headings, and no arbitrary color changes.
- Prefer single-column pages for narrative reports unless the user asks for a newsletter or brochure format.
- Use section breaks only when page setup changes, such as landscape tables or appendix material.
- Keep heading levels shallow. Most business documents need `Title`, `Heading 1`, `Heading 2`, and body styles.
- Treat images, charts, and screenshots as evidence. Size them to be legible in PDF, not merely visible in Word.
- Add a table of contents when the document is long enough that navigation matters.

## Non-COM vs COM split

Normal Codex execution can prepare source text, outline structure, tables, image assets, style decisions, and review notes without Word COM.

True Word COM is required to prove or perform:

- pagination and page statistics,
- table of contents and field updates,
- comments and tracked changes in the live Word object model,
- legacy `.doc` conversion,
- PDF export,
- repair-free open/save behavior.

If COM preflight fails in Codex, continue preparing the non-COM inputs and move only the Word automation step to a signed-in desktop-user PowerShell session or the self-hosted Office runner.

## Contribution to design upskill

This reference teaches Codex to reason about Word documents as rendered, reviewable artifacts rather than text containers. It gives the agent a vocabulary for layout fidelity, style semantics, review state, and PDF evidence when there is no template to copy.
