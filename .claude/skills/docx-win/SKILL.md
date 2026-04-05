---
name: docx-win
description: native microsoft word automation for windows .docx workflows. use when chatgpt or codex is running on windows with microsoft word installed and needs to create, edit, review, convert, or verify word documents through word com automation. trigger for .docx or .doc requests, professional word deliverables, tracked changes, comments, find and replace, table of contents, headers and footers, page numbering, layout-sensitive edits, or exporting a word document to pdf for review. prefer this skill over libreoffice-based document workflows when word is available.
disable-model-invocation: true
---

# DOCX Win

## Notes

### Provenance

- Upstream repo: `https://github.com/anthropics/skills`
- Source folder: `skills/docx`
- Source branch: `main`

### Porting Notes

- This is a light Windows-specific port of Anthropic's `docx` skill for Codex.
- The upstream skill centers on OOXML unpack/edit flows plus LibreOffice-backed conversion and accept-changes helpers.
- This port changes the default execution path to PowerShell wrappers around Microsoft Word COM so Word handles create, edit, review, comments, revisions, fields, pagination, and PDF export directly.
- It remains Windows-only because reliable execution depends on a local Microsoft Word desktop installation and COM automation.

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

## Preflight

For a new machine or after an Office repair/update, run:

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\smoke-test.ps1
```

The smoke test proves that:
- Word COM automation can start.
- A document can be created and saved.
- Tracked changes and comments work.
- A PDF export works.
- Page statistics can be computed.

If the smoke test fails, stop and fix the local Word/Office environment before attempting production edits.

## Default operating rules

- Prefer PowerShell scripts in `docx-win\scripts\` over ad hoc GUI interaction.
- Keep `Word.Application.Visible = $false` unless visual debugging is required.
- Set `DisplayAlerts = 0` to avoid blocking prompts.
- Work on a copy unless the user clearly wants in-place edits.
- Save output as `.docx` unless the user explicitly requests another format.
- For legacy `.doc`, convert to `.docx` first.
- For layout-sensitive work, export a PDF after meaningful changes and inspect that PDF.
- Before final delivery, update all fields and tables of contents, then save again.
- Always close the document and quit Word in `finally` blocks.
- Always release COM objects. Orphaned `WINWORD.EXE` processes are a reliability bug.

## Common commands

Run all commands from the root of this repository.

### Convert legacy `.doc` to `.docx`

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\convert-doc-to-docx.ps1 -InputPath .\input.doc -OutputPath .\input.docx
```

### Export `.docx` to PDF for review

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\export-pdf.ps1 -InputPath .\report.docx -OutputPath .\report.pdf
```

### Accept all tracked changes

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\accept-revisions.ps1 -InputPath .\draft.docx -OutputPath .\clean.docx
```

### Find and replace across the document

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\find-replace.ps1 -InputPath .\draft.docx -FindText "Old Name" -ReplaceText "New Name" -OutputPath .\draft-updated.docx
```

### Add a comment to a specific range

```powershell
powershell -ExecutionPolicy Bypass -File docx-win\scripts\add-comment.ps1 -InputPath .\draft.docx -Start 1 -End 25 -CommentText "verify this figure" -Author "Claude" -Initials "CC" -OutputPath .\draft-commented.docx
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

Use `docx-win\references\word-com-recipes.md` for common construction patterns.

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
2. export a PDF with `docx-win\scripts\export-pdf.ps1`,
3. inspect the PDF or page count,
4. fix issues,
5. export again.

For final delivery:

1. update fields,
2. update tables of contents,
3. force repagination by computing page statistics,
4. save the document,
5. export a PDF companion when useful.

## Word COM patterns and references

Load `docx-win\references\word-com-recipes.md` when you need examples for:
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

## Bundled scripts

All scripts live in `docx-win\scripts\` relative to the repository root.

- `word-common.ps1`: shared helpers for Word COM startup, cleanup, save, field refresh, PDF export, and path handling.
- `convert-doc-to-docx.ps1`: convert legacy `.doc` to `.docx`.
- `export-pdf.ps1`: export a `.docx` to PDF.
- `accept-revisions.ps1`: open a document and write a clean copy with all revisions accepted.
- `find-replace.ps1`: run Word's native find/replace engine and save output.
- `add-comment.ps1`: add a Word comment to a range and save output.
- `smoke-test.ps1`: end-to-end validation for the local Windows + Word automation environment.

## Failure handling

If Word cannot be automated:
- confirm the machine is Windows,
- confirm Microsoft Word launches manually,
- rerun `docx-win\scripts\smoke-test.ps1`,
- check for blocked dialogs, protected view, or orphaned `WINWORD.EXE` processes,
- retry with a fresh working copy.

Only fall back to lower-level ZIP/XML repair when Word COM is unavailable or the file is structurally damaged in a way Word cannot fix.
