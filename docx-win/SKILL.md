---
name: docx-win
description: native microsoft word automation for windows .docx workflows. use when chatgpt or codex is running on windows with microsoft word installed and needs to create, edit, review, convert, or verify word documents through word com automation. trigger for .docx or .doc requests, professional word deliverables, no-template document polish, tracked changes, comments, find and replace, table of contents, headers and footers, page numbering, layout-sensitive edits, or exporting a word document to pdf for review. prefer this skill over libreoffice-based document workflows when word is available.
---

# DOCX Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/docx`
- Source branch: `main`

### Porting Notes

- This is a Windows COM adaptation of Anthropic's `docx` skill for Codex.
- The upstream skill centers on OOXML unpack/edit flows plus LibreOffice-backed conversion and accept-changes helpers.
- This port changes the default execution path to PowerShell wrappers around Microsoft Word COM so Word handles create, edit, review, comments, revisions, fields, pagination, and PDF export directly.
- It remains Windows-only because reliable execution depends on a local Microsoft Word desktop installation and COM automation.

## Design Upskill Contribution

Use `docx-win` to teach Codex how to turn an untemplated brief into a Word document that is structured, reviewable, and render-verified. The skill contributes:

- Word-native style and section discipline instead of manual font-only formatting,
- layout fidelity through Word pagination, field refresh, and PDF evidence,
- review-state handling through comments and tracked changes,
- a clear non-COM versus COM split so Codex can prepare content safely and hand true rendering to Word when required.

Read `references/document-quality-map.md` when a task asks for a polished document, executive memo, report, proposal, or other no-template Word deliverable.

Use Microsoft Word COM automation on Windows as the default engine for `.docx` work.
Do not use LibreOffice when Word is installed.
Do not edit OOXML directly unless Word automation fails and the task truly requires low-level repair.

## Workflow

1. Preflight the machine.
2. Choose create vs edit vs review.
3. Save a working copy before risky changes.
4. Make changes through Word COM.
5. Update fields, pagination, and table of contents before final save.
6. Export to PDF when layout matters.
7. Close Word cleanly and release COM objects.

For no-template document creation or major restyling, use `references/document-quality-map.md` before writing automation so the structure, styles, page system, tables, review state, and PDF proof are planned together.

## Preflight

Before any Word COM step, run the shared Office preflight from a regular PowerShell window opened as the signed-in desktop user:

```powershell
& "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps Word
```

That path assumes a Codex-style install. If this skill is loaded through a Claude Code plugin instead, resolve the same script from the plugin cache first:

```powershell
$preflight = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache" -Recurse -Filter "office_com_preflight.ps1" -ErrorAction SilentlyContinue | Select-Object -First 1).FullName
if (-not $preflight) { $preflight = "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" }
& $preflight -Apps Word
```

If preflight reports `can_use_com = false`, do not create `Word.Application` from the Codex sandbox. Prepare non-COM inputs in Codex and run the Word COM step from that desktop-user PowerShell window through `scripts/invoke-docx-win.ps1` or a task-specific script.

For a new machine or after an Office repair/update, run:

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action smoke-test
```

The smoke test proves that:
- Word COM automation can start.
- A document can be created and saved.
- Tracked changes and comments work.
- A PDF export works.
- Page statistics can be computed.

If the smoke test fails, stop and fix the local Word/Office environment before attempting production edits.

## Default operating rules

- Prefer PowerShell scripts in `scripts/` over ad hoc GUI interaction.
- Keep `Word.Application.Visible = $false` unless visual debugging is required.
- Set `DisplayAlerts = 0` to avoid blocking prompts.
- Work on a copy unless the user clearly wants in-place edits.
- Save output as `.docx` unless the user explicitly requests another format.
- For legacy `.doc`, convert to `.docx` first.
- For layout-sensitive work, export a PDF after meaningful changes and inspect that PDF.
- For no-template deliverables, use Word styles, sections, fields, tables, and inline shapes as design structures rather than only changing visible text formatting.
- Before final delivery, update all fields and tables of contents, then save again.
- Always close the document and quit Word in `finally` blocks.
- Always release COM objects. Orphaned `WINWORD.EXE` processes are a reliability bug.
- Never call `New-Object -ComObject Word.Application` directly from the Codex sandbox. Use the shared preflight and then run COM work from the signed-in desktop user session through `scripts/invoke-docx-win.ps1` or a task-specific script.

## Common commands

### Convert legacy `.doc` to `.docx`

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action convert-doc-to-docx -InputPath .\input.doc -OutputPath .\input.docx
```

### Export `.docx` to PDF for review

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action export-pdf -InputPath .\report.docx -OutputPath .\report.pdf
```

### Accept all tracked changes

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action accept-revisions -InputPath .\draft.docx -OutputPath .\clean.docx
```

### Find and replace across the document

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action find-replace -InputPath .\draft.docx -FindText "Old Name" -ReplaceText "New Name" -OutputPath .\draft-updated.docx
```

### Add a comment to a specific range

```powershell
& "$env:USERPROFILE\.codex\skills\docx-win\scripts\invoke-docx-win.ps1" -Action add-comment -InputPath .\draft.docx -Start 1 -End 25 -CommentText "verify this figure" -Author "Codex" -Initials "CX" -OutputPath .\draft-commented.docx
```

## Decide the path

### Creating a new document

Use Word COM to build the document directly when the user needs a polished Word deliverable.
Prefer built-in styles such as `Title`, `Heading 1`, `Heading 2`, and `Normal` instead of manual font-only formatting.
Use tables, headers, footers, page numbers, and images through COM objects rather than raw XML.
After creating content:

1. update fields,
2. update tables of contents if present,
3. compute page statistics,
4. save the `.docx`,
5. export a PDF when layout matters.

Use `references/word-com-recipes.md` for common construction patterns.
Use `references/document-quality-map.md` to decide the document structure, page system, visual evidence, and verification loop when no template exists.

### Editing an existing document

Open the document in Word COM and preserve its native Word behavior.
For text edits, prefer direct `Range` operations or the Find/Replace engine.
For style-aware edits, target paragraphs, tables, sections, headers, and footers explicitly.
For layout-sensitive work, export a PDF after each meaningful stage.

When the user wants a clean deliverable:
- accept revisions only if the user asked for a clean copy,
- remove comments only if the user asked for them removed,
- update fields and TOC before final save.

When the user wants review markup preserved:
- leave `TrackRevisions` enabled before making edits,
- add comments through Word comments,
- save a reviewed copy separately from any clean copy.

### Reviewing and redlining

Use Word-native review features through COM.

- Turn on tracked changes with `$doc.TrackRevisions = $true` before making edits.
- Add comments through `$doc.Comments.Add(...)`.
- Accept all revisions through `$doc.Revisions.AcceptAll()` when a clean copy is required.
- Update fields after accepting revisions because pagination and references may change.

## Verification standard

Use this verification loop whenever formatting or pagination matters:

1. save the `.docx`,
2. export a PDF with `scripts/export-pdf.ps1`,
3. inspect the PDF or page count,
4. fix issues,
5. export again.

For final delivery:

1. update fields,
2. update tables of contents,
3. force repagination by computing page statistics,
4. save the document,
5. export a PDF companion when useful.

For no-template deliverables, also verify the relevant dimensions in `references/document-quality-map.md`: style hierarchy, page system, tables, figures, review artifacts, field behavior, and PDF evidence.

## Word COM patterns and references

Load `references/word-com-recipes.md` when you need examples for:
- headings and styles,
- tables,
- headers and footers,
- page numbers,
- images,
- find and replace,
- comments and tracked changes,
- field and TOC refresh,
- PDF export,
- COM cleanup.

Load `references/document-quality-map.md` when the task requires:
- no-template document design,
- executive-report or proposal polish,
- style hierarchy decisions,
- table and figure layout checks,
- a clear non-COM versus Word COM verification split.

## Bundled scripts

- `scripts/word-common.ps1`: shared helpers for Word COM startup, cleanup, save, field refresh, PDF export, and path handling.
- `scripts/convert-doc-to-docx.ps1`: convert legacy `.doc` to `.docx`.
- `scripts/export-pdf.ps1`: export a `.docx` to PDF.
- `scripts/accept-revisions.ps1`: open a document and write a clean copy with all revisions accepted.
- `scripts/find-replace.ps1`: run Word's native find/replace engine and save output.
- `scripts/add-comment.ps1`: add a Word comment to a range and save output.
- `scripts/smoke-test.ps1`: end-to-end validation for the local Windows + Word automation environment.

## Failure handling

If Word cannot be automated:
- confirm the machine is Windows,
- confirm Microsoft Word launches manually,
- rerun `scripts/invoke-docx-win.ps1 -Action smoke-test`,
- check for blocked dialogs, protected view, or orphaned `WINWORD.EXE` processes,
- retry with a fresh working copy.

If Word COM throws `0x80070520`, treat that as a wrong-session problem, not as a document problem. Move the COM step to the signed-in desktop user session and rerun it there.

Only fall back to lower-level ZIP/XML repair when Word COM is unavailable or the file is structurally damaged in a way Word cannot fix.
