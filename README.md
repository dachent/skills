# llm agent skills

[![Validate](https://github.com/dachent/skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dachent/skills/actions/workflows/validate.yml)

Focused Codex and Claude skills, currently centered on Windows Office automation plus reusable research and planning workflows.

Canonical GitHub About settings:
- Description: `Windows-native Codex skills for Word, PowerPoint, and Excel using Microsoft Office COM automation.`
- Topics: `codex`, `skills`, `windows`, `powershell`, `python`, `microsoft-office`, `office-automation`, `word`, `powerpoint`, `excel`, `com-automation`
- Homepage: leave blank until the repository has a real external docs or project site

## Why This Repo Exists

This repository started as a home for Office-oriented skills ported from Anthropic's `skills` repository into Codex-friendly Windows workflows.

It now also hosts narrowly scoped original skills when the workflow is stable, reusable, and benefits from explicit operating guidance. The current catalog is still Office-heavy, but not Office-exclusive.

For the Office skills, the core design choice remains deliberate: prefer local Microsoft Office desktop automation over LibreOffice-style file transformation whenever Word, PowerPoint, or Excel fidelity matters. Those skills are Windows-specific and environment-dependent by design.

The Office COM entrypoints now share a common runtime for session preflight, input-desktop checks, and normalized reroute behavior when COM is unavailable from a sandboxed or non-interactive shell.

The shared visual runtime gives future Codex visual skills a browser and image evidence layer for no-template design work. It is separate from Office COM and supports a render-inspect-lint-revise loop with screenshots, console capture, PDF export, image bounds, and contact sheets.

## Skill Catalog

| Skill | Engine | Upstream source | Smoke test |
| --- | --- | --- | --- |
| [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | Codex hostile plan review | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live flawed-plan fixture plus repo metadata validation |
| [`artifact-runtime-codex`](./artifact-runtime-codex) | Browser runtime handoff + evidence bundles | repo-owned original | Visual skills contract validation |
| [`canvas-design-codex`](./canvas-design-codex) | Canvas, SVG, WebGL, and pixel evidence QA | repo-owned original | Visual skills contract validation |
| [`deep-planning-codex`](./deep-planning-codex) | Codex-native gated planning workflow | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live subagent forward-tests plus artifact validator |
| [`docx-win`](./docx-win) | Microsoft Word COM + no-template document polish | `anthropics/skills` -> `skills/docx` | `powershell -ExecutionPolicy Bypass -File .\docx-win\scripts\smoke-test.ps1` |
| [`frontend-design-codex`](./frontend-design-codex) | Responsive frontend design + screenshot QA | repo-owned original | Visual skills contract validation |
| [`grill-me-codex`](./grill-me-codex) | Codex read-only design interview | `mattpocock/skills` -> `skills/productivity/grill-me` | Live interview scenario tests plus repo metadata validation |
| [`grill-with-docs-codex`](./grill-with-docs-codex) | Codex docs-backed design interview | `mattpocock/skills` -> `skills/engineering/grill-with-docs` | Live docs fixture tests plus repo metadata validation |
| [`handoff-codex`](./handoff-codex) | Codex continuation document workflow | `mattpocock/skills` -> `skills/productivity/handoff` | Temp-file handoff scenario plus repo metadata validation |
| [`pptx-win`](./pptx-win) | Microsoft PowerPoint COM + no-template deck design, OOXML fallback | `anthropics/skills` -> `skills/pptx` | `powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\smoke_test.ps1` |
| [`repo-map-codex`](./repo-map-codex) | Codex project and evidence mapping | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live mixed-project fixture plus repo metadata validation |
| [`theme-factory-codex`](./theme-factory-codex) | Design tokens, palettes, and theme QA | repo-owned original | Visual skills contract validation |
| [`web-artifacts-builder-codex`](./web-artifacts-builder-codex) | Standalone web artifact packaging + visual evidence | repo-owned original | Visual skills contract validation |
| [`xlsx-win`](./xlsx-win) | Microsoft Excel COM + chart-ready workbook reliability | `anthropics/skills` -> `skills/xlsx` | `powershell -ExecutionPolicy Bypass -File .\xlsx-win\scripts\self_test_xlsx_win.ps1` |
| [`ultraplan-codex`](./ultraplan-codex) | Codex-native deep implementation planning workflow | `6missedcalls/ultraplan` -> `.` | Live subagent forward-tests plus repo metadata validation |
| [`verification-plan-codex`](./verification-plan-codex) | Codex proof and rollback planning | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live verification fixture plus Python artifact validation |

## Prerequisites

- Codex or Claude configured to load local skills from your skills directory
- For `docx-win`, `pptx-win`, and `xlsx-win`: Windows with a local interactive desktop session
- For `docx-win`, `pptx-win`, and `xlsx-win`: Microsoft 365 desktop apps installed for the relevant skill
- PowerShell for the Office automation entrypoints and repo validation scripts
- Python 3 for the bundled Python helpers and repo tooling
- Node.js and npm for `.shared/visual-runtime` Playwright helper validation
- For `ultraplan-codex`: a Codex session that can read the target codebase and write `.ultraplan/plan.md`
- For `grill-me-codex`: a Codex session that can read the target codebase or artifacts before asking the user discoverable questions
- For `grill-with-docs-codex`: permission to update project documentation such as `CONTEXT.md` and accepted ADRs
- For `handoff-codex`: permission to write a redacted continuation document to the operating system temporary directory
- For the Codex deep planning suite: permission to create or update `.deep-planning/` planning artifacts in the target project, and optionally `.ultraplan/plan.md` when `ultraplan-codex` is part of the selected workflow

## Design Upskill Provenance

The Office skills are the first foundation for upskilling Codex on no-template design work. Before adding stronger deck, document, spreadsheet, and visual artifact behavior, the repository pins the upstream source used for each Office-derived skill and documents why the local Windows/Codex implementation intentionally diverges.

This matters because no-template design quality depends on more than attractive output. Codex needs traceable guidance for:

- which upstream skill behavior is being adapted;
- why local Windows Office COM automation is the fidelity path;
- which changes are meant to improve layout, rendering, screenshot review, and repair loops;
- which checks can run in normal Codex execution and which checks require a desktop-user or elevated Office COM context.

The lock file is `.upstream/anthropic-skills.lock.json`. Each in-scope Office skill has a `PROVENANCE.md` file with source, port classification, intentional divergences, design-upskill contribution, and COM boundary notes.

`pptx-win` is the first Office skill to add a no-template visual design layer on top of provenance: it now includes deck concepting guidance, reusable layout patterns, a screenshot QA rubric, render/inspect guidance, non-COM metadata inspection, static text-density risk checks, and visual QA fixtures. True rendering, PDF export, and text-bound verification still require PowerPoint COM from a desktop-user/elevated session or the Office runner.

`docx-win` and `xlsx-win` now extend that design-upskill foundation beyond decks. `docx-win` documents how Word styles, sections, tables, review markup, field refresh, and PDF evidence contribute to polished no-template documents. `xlsx-win` documents how calculation correctness, Power Query load behavior, formula-error checks, and chart-ready output tables contribute to trustworthy no-template visuals. Both skills explicitly split normal Codex preparation from true Office COM work that may need desktop-user or elevated PowerShell.

`.shared/visual-runtime` is the browser-native layer for future visual skills. It gives Codex reusable scripts and references for screenshot capture, console capture, visual lint, PDF export, image bounds inspection, contact sheets, accessibility checks, and design-token discipline. This phase requires no Office COM: browser rendering and image inspection can run in normal Codex execution, while later Office embedding or export still belongs to the Office COM skills.

Codex visual skills now consume that runtime directly. `frontend-design-codex`, `web-artifacts-builder-codex`, `theme-factory-codex`, `canvas-design-codex`, and `artifact-runtime-codex` each document what they teach Codex, why the lesson matters when no template exists, how `.shared\visual-runtime` supplies screenshot/visual-lint/evidence loops, and how users or agents should verify the result. These skills are browser-first and do not require Office COM.

## Installation

### Codex

1. Clone this repository locally.
2. Copy the shared runtime folders `.shared\office-com` and `.shared\visual-runtime`, plus the skill folders you want to use, into your Codex skills directory, for example `%USERPROFILE%\.codex\skills\`.
3. Keep the directory names unchanged: `.shared`, `adversarial-plan-review-codex`, `artifact-runtime-codex`, `canvas-design-codex`, `deep-planning-codex`, `docx-win`, `frontend-design-codex`, `grill-me-codex`, `grill-with-docs-codex`, `handoff-codex`, `pptx-win`, `repo-map-codex`, `theme-factory-codex`, `ultraplan-codex`, `verification-plan-codex`, `web-artifacts-builder-codex`, and `xlsx-win`.
4. Use the skill by name from Codex, for example `$deep-planning-codex`, `$repo-map-codex`, `$verification-plan-codex`, `$adversarial-plan-review-codex`, `$artifact-runtime-codex`, `$canvas-design-codex`, `$docx-win`, `$frontend-design-codex`, `$grill-me-codex`, `$grill-with-docs-codex`, `$handoff-codex`, `$pptx-win`, `$theme-factory-codex`, `$ultraplan-codex`, `$web-artifacts-builder-codex`, or `$xlsx-win`.
5. Before relying on Excel, PowerPoint, or Word COM from a new machine or session, run the shared preflight from a signed-in desktop-user PowerShell window:

   ```powershell
   & "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps @('Excel','PowerPoint','Word')
   ```

6. Run the relevant smoke test or live validation before relying on a new machine or session.

### Claude Code

1. Clone this repository locally.
2. In your project's `.claude/skills/` directory, copy or symlink the desired subdirectories from `.claude/skills/` in this repository: `docx-win`, `pptx-win`, and `xlsx-win`.
3. If you plan to use the Office skills, also copy the shared runtime folder `.shared\office-com` from this repository into `.claude\skills\.shared\office-com` so the skill wrappers can resolve their shared preflight module. If you plan to use browser visual QA helpers, copy `.shared\visual-runtime` as well.
4. Keep the directory names unchanged.
5. Reference each skill from a `CLAUDE.md` or system prompt by its name, for example `docx-win`, `pptx-win`, or `xlsx-win`.
6. Run the relevant smoke test or live validation before relying on a new machine or session.

## Validation And CI

The repository uses a two-tier validation model.

Hosted validation runs in GitHub Actions on `windows-latest`:
- YAML parse and required-field validation for every `agents/openai.yaml`
- `SKILL.md` front matter and internal `scripts/...` and `references/...` path validation
- PowerShell parser checks plus `PSScriptAnalyzer` with a repo-owned rule set
- Python syntax compilation for the bundled `.py` files
- shared visual runtime contract validation plus JavaScript syntax checks through npm

Office runtime validation is separate because GitHub-hosted runners do not provide reliable Microsoft Office COM automation:
- `.github/workflows/office-smoke.yml` is designed for a self-hosted Windows runner labeled `office`
- it runs the Word, PowerPoint, and Excel smoke tests
- it uploads logs and generated artifacts for debugging
- it can be started manually or requested from a pull request with `/office-smoke`


Planning workflow skills use live agent validation instead of runtime smoke scripts. For `ultraplan-codex`, the validation covers baseline planning, normal skill-guided planning, existing-plan refinement, parallel-agent fallback behavior, and report-only planning in a non-Git fixture.

The Codex deep planning suite was adapted from the `deep_planning.txt` gist at revision `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`. Unlike the Claude-native source prompt, the Codex version is split into a master orchestrator plus focused companion skills. Slash-command choreography is replaced with Codex skill invocation, Claude handoff loops are replaced with durable `.deep-planning/` artifacts, model routing is replaced with phase contracts and optional subagent strategy, and execution safety is enforced through write scopes, proceed gates, and artifact validation.

Interactive workflow skills use scenario validation. For `grill-me-codex`, validation covers one-question-at-a-time plan interrogation and repo exploration before asking discoverable questions. For `grill-with-docs-codex`, validation covers `CONTEXT.md` discovery, lazy docs creation, glossary-only updates, and ADR gating. For `handoff-codex`, validation covers temp-directory output, redaction, artifact references, and suggested skill handoff content.

Local validation commands:

```powershell
pwsh -NoLogo -NoProfile -File .\tools\validate_repo.ps1
pwsh -NoLogo -NoProfile -File .\tools\validate_powershell.ps1 -SettingsPath .github\PSScriptAnalyzerSettings.psd1
python .\tools\validate_provenance.py
python .\tools\check_upstream_drift.py --json .\.upstream\reports\latest-drift.json
python .\tools\generate_alignment_report.py --json .\.upstream\reports\latest-drift.json --markdown .\.upstream\reports\latest-alignment-report.md
python .\tools\test_deep_planning_validator.py
python .\tools\test_office_com_contract.py
python .\tools\test_visual_runtime_contract.py
python .\tools\test_visual_skills_contract.py
Push-Location .shared\visual-runtime
npm ci --ignore-scripts
npm run check
Pop-Location
$compilePaths = @('.\tools')
$compilePaths += Get-ChildItem -Path . -Directory -Recurse -Filter scripts |
  Where-Object { $_.FullName -notmatch '\\node_modules\\' } |
  ForEach-Object { $_.FullName }
python -m compileall -q @compilePaths
```

## Repo Layout

- [`.upstream/`](./.upstream): pinned upstream source metadata, Office skill snapshots, and generated alignment reports
- [`.shared/office-com/`](./.shared/office-com): shared Office COM preflight and guard runtime used by Excel, PowerPoint, and Word wrappers
- [`.shared/visual-runtime/`](./.shared/visual-runtime): shared Playwright and image utilities for browser screenshot evidence, visual lint, PDF export, image bounds, and contact sheets
- [`adversarial-plan-review-codex/`](./adversarial-plan-review-codex): Codex hostile review skill for execution plans
- [`artifact-runtime-codex/`](./artifact-runtime-codex): runtime and evidence handoff skill for browser visual artifacts
- [`canvas-design-codex/`](./canvas-design-codex): drawn-visual QA skill for canvas, SVG, WebGL, and pixel evidence
- [`deep-planning-codex/`](./deep-planning-codex): master Codex deep planning workflow skill
- [`docx-win/`](./docx-win): Word skill, scripts, no-template document quality references, and agent metadata
- [`frontend-design-codex/`](./frontend-design-codex): frontend UI design skill using screenshots, visual lint, and responsive QA
- [`grill-me-codex/`](./grill-me-codex): read-only plan and design grilling interview skill adapted from `mattpocock/skills`
- [`grill-with-docs-codex/`](./grill-with-docs-codex): docs-backed plan grilling skill with context and ADR references adapted from `mattpocock/skills`
- [`handoff-codex/`](./handoff-codex): redacted continuation handoff skill adapted from `mattpocock/skills`
- [`pptx-win/`](./pptx-win): PowerPoint skill, scripts, references, fallback OOXML utilities, and agent metadata
- [`pptx-win/tests/fixtures/`](./pptx-win/tests/fixtures): no-template deck briefs and expected visual QA notes for non-COM agent rehearsal
- [`repo-map-codex/`](./repo-map-codex): Codex project map and evidence catalog skill
- [`theme-factory-codex/`](./theme-factory-codex): theme and design-token skill for no-template visual systems
- [`ultraplan-codex/`](./ultraplan-codex): Codex-native deep implementation planning skill adapted from `6missedcalls/ultraplan`
- [`verification-plan-codex/`](./verification-plan-codex): Codex proof criteria and rollback planning skill
- [`web-artifacts-builder-codex/`](./web-artifacts-builder-codex): standalone web artifact creation and evidence packaging skill
- [`xlsx-win/`](./xlsx-win): Excel skill, scripts, workbook reliability references, and agent metadata
- [`.github/workflows/`](./.github/workflows): hosted validation and self-hosted Office smoke workflows
- [`tools/`](./tools): repository validation helpers used by CI and local contributors

## Contributing

Contributions should preserve each skill's documented contract:

- keep the Office skills Windows-specific and COM-first unless the skill explicitly documents a fallback path
- keep docs-first skills concise, reproducible, and explicit about any search/open constraints
- keep interactive workflow skills strict about their write scope, especially `handoff-codex` temp files and `grill-with-docs-codex` documentation-only edits
- keep planning workflow skills strict about `.deep-planning/` write scopes, proceed gates, and evidence-backed validation
- update `agents/openai.yaml` together with any skill behavior changes
- keep `SKILL.md` examples and referenced scripts in sync
- document no-template design changes with what changed, why it improves Codex's judgment, and how rendered evidence or static risk reports verify the output
- run the hosted validation commands locally before opening a PR
- request the Office smoke workflow when a change affects runtime Office automation behavior

## Licensing And Provenance

This repository records provenance for each skill but does not currently publish a root `LICENSE` file.

Before redistributing or repackaging this repository, review the upstream provenance and decide on an explicit licensing policy for the repo as a whole.

Current Anthropic-derived Office provenance is pinned in `.upstream/anthropic-skills.lock.json`. Snapshot folders under `.upstream/anthropic-skills/57546260929473d4e0d1c1bb75297be2fdfa1949/` preserve upstream comparison baselines and `LICENSE.txt` files. Upstream drift is reported by `.github/workflows/upstream-drift.yml`; invalid provenance fails validation.

Current upstream provenance:

| Skill | Upstream repo | Source folder | Source branch | Port depth |
| --- | --- | --- | --- | --- |
| `adversarial-plan-review-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `artifact-runtime-codex` | `dachent/skills` | `artifact-runtime-codex` | repo-owned original | Original Codex visual design skill |
| `canvas-design-codex` | `dachent/skills` | `canvas-design-codex` | repo-owned original | Original Codex visual design skill |
| `deep-planning-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `docx-win` | `https://github.com/anthropics/skills` | `skills/docx` | `main` pinned at `57546260929473d4e0d1c1bb75297be2fdfa1949` (`2026-06-15`) | Windows COM adaptation |
| `frontend-design-codex` | `dachent/skills` | `frontend-design-codex` | repo-owned original | Original Codex visual design skill |
| `grill-me-codex` | `https://github.com/mattpocock/skills` | `skills/productivity/grill-me` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Light Codex adaptation |
| `grill-with-docs-codex` | `https://github.com/mattpocock/skills` | `skills/engineering/grill-with-docs` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Medium Codex adaptation |
| `handoff-codex` | `https://github.com/mattpocock/skills` | `skills/productivity/handoff` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Light Codex adaptation |
| `pptx-win` | `https://github.com/anthropics/skills` | `skills/pptx` | `main` pinned at `57546260929473d4e0d1c1bb75297be2fdfa1949` (`2026-06-15`) | Windows COM adaptation |
| `repo-map-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `theme-factory-codex` | `dachent/skills` | `theme-factory-codex` | repo-owned original | Original Codex visual design skill |
| `ultraplan-codex` | `https://github.com/6missedcalls/ultraplan` | `.` | `main` at `06779940475f9c52b4d3b546d309b2c31ebbf8ea` (`2026-03-31T21:48:42Z`) | Heavy Codex adaptation |
| `verification-plan-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `web-artifacts-builder-codex` | `dachent/skills` | `web-artifacts-builder-codex` | repo-owned original | Original Codex visual design skill |
| `xlsx-win` | `https://github.com/anthropics/skills` | `skills/xlsx` | `main` pinned at `57546260929473d4e0d1c1bb75297be2fdfa1949` (`2026-06-15`) | Heavy Windows COM adaptation |
