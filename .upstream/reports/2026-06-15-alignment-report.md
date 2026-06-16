# Upstream Alignment Report

- Pinned upstream commit: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Current upstream commit: `57546260929473d4e0d1c1bb75297be2fdfa1949`
- Upstream changed: `false`

## Skills

| Skill | Source | Upstream path | Snapshot | Provenance | Upstream diff | Local diff | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| docx-win | anthropic-skills | `skills/docx` | yes | yes | 0 | 87 | `review_required` |
| pptx-win | anthropic-skills | `skills/pptx` | yes | yes | 0 | 87 | `review_required` |
| xlsx-win | anthropic-skills | `skills/xlsx` | yes | yes | 0 | 79 | `review_required` |

## docx-win

### Upstream Changes Since Pin

No file-level changes detected.

### Local Folder Compared To Pinned Snapshot

- added: 11
  - `PROVENANCE.md`
  - `agents/openai.yaml`
  - `references/word-com-recipes.md`
  - `scripts/accept-revisions.ps1`
  - `scripts/add-comment.ps1`
  - `scripts/convert-doc-to-docx.ps1`
  - `scripts/export-pdf.ps1`
  - `scripts/find-replace.ps1`
  - `scripts/invoke-docx-win.ps1`
  - `scripts/smoke-test.ps1`
  - `scripts/word-common.ps1`
- removed: 75
  - `LICENSE.txt`
  - `scripts/__init__.py`
  - `scripts/__pycache__/__init__.cpython-310.pyc`
  - `scripts/__pycache__/accept_changes.cpython-310.pyc`
  - `scripts/__pycache__/comment.cpython-310.pyc`
  - `scripts/accept_changes.py`
  - `scripts/comment.py`
  - `scripts/office/__pycache__/pack.cpython-310.pyc`
  - `scripts/office/__pycache__/soffice.cpython-310.pyc`
  - `scripts/office/__pycache__/unpack.cpython-310.pyc`
  - `scripts/office/__pycache__/validate.cpython-310.pyc`
  - `scripts/office/helpers/__init__.py`
  - `scripts/office/helpers/__pycache__/__init__.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/merge_runs.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/simplify_redlines.cpython-310.pyc`
  - `scripts/office/helpers/merge_runs.py`
  - `scripts/office/helpers/simplify_redlines.py`
  - `scripts/office/pack.py`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd`
  - ... 50 more
- changed: 1
  - `SKILL.md`

## pptx-win

### Upstream Changes Since Pin

No file-level changes detected.

### Local Folder Compared To Pinned Snapshot

- added: 13
  - `PROVENANCE.md`
  - `agents/openai.yaml`
  - `references/ooxml-fallback.md`
  - `references/powerpoint-com-workflow.md`
  - `references/troubleshooting.md`
  - `scripts/export_pdf.ps1`
  - `scripts/export_slides.ps1`
  - `scripts/invoke-pptx-win.ps1`
  - `scripts/pptx_com.psm1`
  - `scripts/presentation_report.ps1`
  - `scripts/replace_text.ps1`
  - `scripts/requirements.txt`
  - `scripts/smoke_test.ps1`
- removed: 9
  - `LICENSE.txt`
  - `editing.md`
  - `pptxgenjs.md`
  - `scripts/__init__.py`
  - `scripts/__pycache__/__init__.cpython-310.pyc`
  - `scripts/__pycache__/thumbnail.cpython-310.pyc`
  - `scripts/office/__pycache__/soffice.cpython-310.pyc`
  - `scripts/office/soffice.py`
  - `scripts/thumbnail.py`
- changed: 65
  - `SKILL.md`
  - `scripts/__pycache__/add_slide.cpython-310.pyc`
  - `scripts/__pycache__/clean.cpython-310.pyc`
  - `scripts/add_slide.py`
  - `scripts/clean.py`
  - `scripts/office/__pycache__/pack.cpython-310.pyc`
  - `scripts/office/__pycache__/unpack.cpython-310.pyc`
  - `scripts/office/__pycache__/validate.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/__init__.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/merge_runs.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/simplify_redlines.cpython-310.pyc`
  - `scripts/office/helpers/merge_runs.py`
  - `scripts/office/helpers/simplify_redlines.py`
  - `scripts/office/pack.py`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd`
  - ... 40 more

## xlsx-win

### Upstream Changes Since Pin

No file-level changes detected.

### Local Folder Compared To Pinned Snapshot

- added: 12
  - `PROVENANCE.md`
  - `agents/openai.yaml`
  - `references/power-query-excel-com.md`
  - `references/spreadsheet-standards.md`
  - `references/windows-excel-refresh.md`
  - `scripts/__pycache__/check_formula_errors.cpython-310.pyc`
  - `scripts/check_formula_errors.ps1`
  - `scripts/check_formula_errors.py`
  - `scripts/invoke-xlsx-win.ps1`
  - `scripts/power_query_excel.ps1`
  - `scripts/refresh_excel.ps1`
  - `scripts/self_test_xlsx_win.ps1`
- removed: 66
  - `LICENSE.txt`
  - `scripts/__pycache__/recalc.cpython-310.pyc`
  - `scripts/office/__pycache__/pack.cpython-310.pyc`
  - `scripts/office/__pycache__/soffice.cpython-310.pyc`
  - `scripts/office/__pycache__/unpack.cpython-310.pyc`
  - `scripts/office/__pycache__/validate.cpython-310.pyc`
  - `scripts/office/helpers/__init__.py`
  - `scripts/office/helpers/__pycache__/__init__.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/merge_runs.cpython-310.pyc`
  - `scripts/office/helpers/__pycache__/simplify_redlines.cpython-310.pyc`
  - `scripts/office/helpers/merge_runs.py`
  - `scripts/office/helpers/simplify_redlines.py`
  - `scripts/office/pack.py`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chart.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-chartDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-diagram.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-lockedCanvas.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-main.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-picture.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-spreadsheetDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/dml-wordprocessingDrawing.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/pml.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/shared-additionalCharacteristics.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/shared-bibliography.xsd`
  - `scripts/office/schemas/ISO-IEC29500-4_2016/shared-commonSimpleTypes.xsd`
  - ... 41 more
- changed: 1
  - `SKILL.md`

## Policy

Invalid provenance fails validation. Upstream drift and local adaptation drift are review signals until the repository adopts a stricter policy.
