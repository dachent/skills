# LLM agent skills

[![Validate](https://github.com/dachent/skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dachent/skills/actions/workflows/validate.yml)

A curated skill repository built for four distinct purposes:

1. **Native application skill extensions** — forks and adaptations that replace generic file transformation with native Microsoft Office automation, including `docx-win`, `pptx-win`, and `xlsx-win`.
2. **Claude and agent workflow ports for Codex** — established workflows such as Grill Me, Handoff, Deep Planning, and Ultraplan adapted to Codex conventions, tools, permissions, and durable artifact contracts.
3. **Repository-owned specialist skills** — original or locally imported implementations, including Code Mapper and Document Handoff, whose current behavior is maintained here.
4. **A Codex design extension pack** — coordinated visual skills that extend Codex design work with shared browser rendering, screenshot evidence, accessibility review, and artifact QA.

This provenance-and-purpose grouping explains **why a skill belongs here**. Platform, runtime, agent support, and validation remain separate attributes generated from [`skills-manifest.json`](./skills-manifest.json).

## Repository model

`skills-manifest.json` is the operational source of truth for inventory, catalog grouping, ownership, support, provenance classification, packaging, shared runtimes, validation, and any generated agent mirrors. Each top-level skill directory is canonical. See [`docs/repository-contract.md`](./docs/repository-contract.md).

This is a mixed-license repository. Redistribution rights vary by skill and source; see [`docs/licensing-and-redistribution.md`](./docs/licensing-and-redistribution.md) and [`.provenance/source-registry.json`](./.provenance/source-registry.json).

## Skill catalog

<!-- BEGIN GENERATED: skill-catalog -->
<!-- Generated section: skill catalog. Source: skills-manifest.json. Generator: tools/generate_repository_artifacts.py. Do not edit by hand. -->

### Native application skill extensions

Forked or adapted skills that replace generic file handling with native desktop application automation.

| Skill | Purpose | Provenance |
| --- | --- | --- |
| [`docx-win`](./docx-win) | native microsoft word automation for windows .docx workflows. use when chatgpt or codex is running on windows with microsoft word installed and needs to create, edit, review, convert, or verify word documents through word com automation. trigger for .docx or .doc requests, professional word deliverables, no-template document polish, tracked changes, comments, find and replace, table of contents, headers and footers, page numbering, layout-sensitive edits, or exporting a word document to pdf for review. prefer this skill over libreoffice-based document workflows when word is available. | heavy adaptation; `anthropics/skills` |
| [`pptx-win`](./pptx-win) | windows powerpoint automation and no-template deck design support for .pptx files in codex app or other local windows environments with microsoft 365 installed. use when chatgpt needs to open, inspect, edit, create, render, export, or qa powerpoint presentations on windows, especially new decks without a template, existing deck edits, speaker notes, slide images, pdf export, placeholder replacement, visual QA, or smoke testing via native powerpoint com automation. prefer this skill over libreoffice-based flows when powerpoint desktop is available. | heavy adaptation; `anthropics/skills` |
| [`xlsx-win`](./xlsx-win) | Windows-only local Excel Desktop automation skill for `.xlsx`, `.xlsm`, `.xls`, `.csv`, and `.tsv` work that needs workbook fidelity, Excel COM refresh or recalculation, Power Query `Workbook.Queries` creation or update, worksheet table loads, connection-only queries, Data Model loads, chart-ready data, no-template spreadsheet deliverables, or Excel environment self-test. Use when native Excel behavior matters on Windows, including workbook connections, cached values, PivotTables, Power Query, calculation correctness, and macro-sensitive refresh when the user explicitly opts in. Do not use for cloud execution, non-Windows environments, Google Sheets API workflows, or machines without Microsoft 365 Excel desktop installed. | heavy adaptation; `anthropics/skills` |

### Claude and agent workflow ports for Codex

External agent workflows ported or substantially adapted for Codex conventions, tools, and artifact contracts.

| Skill | Purpose | Provenance |
| --- | --- | --- |
| [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | Use when a plan needs hostile review before execution, especially high-risk coding, business deliverables, migrations, no-git changes, weak validation, stale assumptions, rollback gaps, or plans that must be safe for another agent to execute. | medium adaptation; `dachent/cdc05151d047708c290bd4da0aaeed96` |
| [`deep-planning-codex`](./deep-planning-codex) | Use when a project needs deep, gated planning before execution, especially high-stakes coding, failed prior attempts, business deliverables, mixed business-coding work, no-git workflows, or plans that need evidence, probes, verification, and adversarial review. | heavy adaptation; `dachent/cdc05151d047708c290bd4da0aaeed96` |
| [`grill-me-codex`](./grill-me-codex) | Use when the user says grill me, wants to stress-test a plan or design, needs a rigorous interview before committing to a decision, or asks for adversarial product, architecture, or implementation questions. | medium adaptation; `mattpocock/skills` |
| [`grill-with-docs-codex`](./grill-with-docs-codex) | Use when the user wants to stress-test a plan against project terminology, domain language, CONTEXT.md, ADRs, existing docs, or code-backed architectural decisions. | medium adaptation; `mattpocock/skills` |
| [`handoff-codex`](./handoff-codex) | Use when the user asks for a handoff, session summary, context packet, continuation note, or wants another agent or future session to pick up the current work. | medium adaptation; `mattpocock/skills` |
| [`repo-map-codex`](./repo-map-codex) | Use when planning needs a durable project map before execution, especially unfamiliar codebases, no-git folders, business artifact projects, mixed business-coding work, dependency discovery, test command discovery, or evidence cataloging. | medium adaptation; `dachent/cdc05151d047708c290bd4da0aaeed96` |
| [`ultraplan-codex`](./ultraplan-codex) | Use when the user says ultraplan, invokes $ultraplan-codex, wants a thorough plan before coding, needs architectural decisions, asks for a grounded implementation plan, or faces a complex multi-file implementation task. | heavy adaptation; `6missedcalls/ultraplan` |
| [`verification-plan-codex`](./verification-plan-codex) | Use when a plan needs proof criteria before execution, especially coding changes, business deliverables, mixed business-coding projects, acceptance criteria, rollback triggers, manual checks, or final validation design. | medium adaptation; `dachent/cdc05151d047708c290bd4da0aaeed96` |

### Repository-owned specialist skills

Original or locally imported workflows whose current implementation is maintained in this repository.

| Skill | Purpose | Provenance |
| --- | --- | --- |
| [`code-mapper-skill`](./code-mapper-skill) | Maps Python imports, symbol references, artifact use, contracts, catalog relationships, OpenLineage datasets, and selectively triggered CodeQL local value/taint flow. Use for dependency maps, callers, inputs/outputs, APIs/schemas, Backstage relationships, blast radius, and semantic tracing. Works on a local path or Git URL. | repo owned original |
| [`document-handoff`](./document-handoff) | Create a comprehensive project handoff package — workfolder copy + dark-mode HTML memo — from Claude Code or Codex projects. Run at any project milestone. | local source import |

### Codex design extension pack

A coordinated set of visual design skills built around shared browser rendering, evidence, and QA infrastructure.

| Skill | Purpose | Provenance |
| --- | --- | --- |
| [`artifact-runtime-codex`](./artifact-runtime-codex) | Use when Codex needs to run, package, validate, hand off, or debug the runtime for a browser visual artifact, including local server setup, asset paths, evidence bundles, screenshot review artifacts, or no-template visual QA handoff. | repo owned original |
| [`canvas-design-codex`](./canvas-design-codex) | Use when Codex needs to build, revise, debug, or verify canvas, SVG, WebGL, Three.js, custom charting, diagram, game, generative visual, or pixel-based browser artwork where screenshot, pixel, animation, or image bounds evidence matters. | repo owned original |
| [`frontend-design-codex`](./frontend-design-codex) | Use when Codex is building, revising, or reviewing a frontend UI, web app screen, responsive layout, component surface, dashboard view, form flow, or no-template product interface that needs visual polish, accessibility, screenshots, or browser QA. | repo owned original |
| [`theme-factory-codex`](./theme-factory-codex) | Use when Codex needs to create, adapt, audit, or repair a visual theme, design tokens, color palette, typography scale, spacing system, CSS variables, or brand-like styling for a no-template frontend, web artifact, dashboard, or visual deliverable. | repo owned original |
| [`web-artifacts-builder-codex`](./web-artifacts-builder-codex) | Use when Codex needs to create, package, revise, or verify a standalone web artifact such as an HTML report, dashboard, microsite, interactive explainer, data story, or browser-delivered deliverable with screenshots, console capture, and evidence packaging. | repo owned original |
<!-- END GENERATED: skill-catalog -->

## Installation inventory

<!-- BEGIN GENERATED: installation-inventory -->
<!-- Generated section: installation inventory. Source: skills-manifest.json. Generator: tools/generate_repository_artifacts.py. Do not edit by hand. -->

Top-level skill directories are canonical. Copy only the skills required by the target agent, plus listed shared components.

| Skill | Canonical directory | Shared components |
| --- | --- | --- |
| `adversarial-plan-review-codex` | [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | — |
| `artifact-runtime-codex` | [`artifact-runtime-codex`](./artifact-runtime-codex) | `.shared/visual-runtime` |
| `canvas-design-codex` | [`canvas-design-codex`](./canvas-design-codex) | `.shared/visual-runtime` |
| `code-mapper-skill` | [`code-mapper-skill`](./code-mapper-skill) | — |
| `deep-planning-codex` | [`deep-planning-codex`](./deep-planning-codex) | — |
| `document-handoff` | [`document-handoff`](./document-handoff) | — |
| `docx-win` | [`docx-win`](./docx-win) | `.shared/office-com` |
| `frontend-design-codex` | [`frontend-design-codex`](./frontend-design-codex) | `.shared/visual-runtime` |
| `grill-me-codex` | [`grill-me-codex`](./grill-me-codex) | — |
| `grill-with-docs-codex` | [`grill-with-docs-codex`](./grill-with-docs-codex) | — |
| `handoff-codex` | [`handoff-codex`](./handoff-codex) | — |
| `pptx-win` | [`pptx-win`](./pptx-win) | `.shared/office-com` |
| `repo-map-codex` | [`repo-map-codex`](./repo-map-codex) | — |
| `theme-factory-codex` | [`theme-factory-codex`](./theme-factory-codex) | `.shared/visual-runtime` |
| `ultraplan-codex` | [`ultraplan-codex`](./ultraplan-codex) | — |
| `verification-plan-codex` | [`verification-plan-codex`](./verification-plan-codex) | — |
| `web-artifacts-builder-codex` | [`web-artifacts-builder-codex`](./web-artifacts-builder-codex) | `.shared/visual-runtime` |
| `xlsx-win` | [`xlsx-win`](./xlsx-win) | `.shared/office-com` |
<!-- END GENERATED: installation-inventory -->

## Platform and agent matrix

<!-- BEGIN GENERATED: platform-agent-matrix -->
<!-- Generated section: platform and agent matrix. Source: skills-manifest.json. Generator: tools/generate_repository_artifacts.py. Do not edit by hand. -->

| Skill | Platforms | Agents | Status |
| --- | --- | --- | --- |
| [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | `cross-platform` | `codex` | `supported` |
| [`artifact-runtime-codex`](./artifact-runtime-codex) | `cross-platform` | `codex` | `supported` |
| [`canvas-design-codex`](./canvas-design-codex) | `cross-platform` | `codex` | `supported` |
| [`code-mapper-skill`](./code-mapper-skill) | `cross-platform` | `codex` | `supported` |
| [`deep-planning-codex`](./deep-planning-codex) | `cross-platform` | `codex` | `supported` |
| [`document-handoff`](./document-handoff) | `cross-platform` | `codex`, `claude-code` | `supported` |
| [`docx-win`](./docx-win) | `windows` | `codex`, `claude-code` | `supported` |
| [`frontend-design-codex`](./frontend-design-codex) | `cross-platform` | `codex` | `supported` |
| [`grill-me-codex`](./grill-me-codex) | `cross-platform` | `codex` | `supported` |
| [`grill-with-docs-codex`](./grill-with-docs-codex) | `cross-platform` | `codex` | `supported` |
| [`handoff-codex`](./handoff-codex) | `cross-platform` | `codex` | `supported` |
| [`pptx-win`](./pptx-win) | `windows` | `codex`, `claude-code` | `supported` |
| [`repo-map-codex`](./repo-map-codex) | `cross-platform` | `codex` | `supported` |
| [`theme-factory-codex`](./theme-factory-codex) | `cross-platform` | `codex` | `supported` |
| [`ultraplan-codex`](./ultraplan-codex) | `cross-platform` | `codex` | `supported` |
| [`verification-plan-codex`](./verification-plan-codex) | `cross-platform` | `codex` | `supported` |
| [`web-artifacts-builder-codex`](./web-artifacts-builder-codex) | `cross-platform` | `codex` | `supported` |
| [`xlsx-win`](./xlsx-win) | `windows` | `codex`, `claude-code` | `supported` |
<!-- END GENERATED: platform-agent-matrix -->

## Prerequisites

Common repository tooling:

- Python 3.12 for validation and bundled helpers;
- Node.js for `document-handoff` tests and runtime;
- PowerShell and Microsoft 365 desktop applications for Windows Office skills;
- Playwright-compatible browser tooling for the visual runtime.

## Validation

<!-- BEGIN GENERATED: validation-summary -->
<!-- Generated section: validation summary. Source: skills-manifest.json. Generator: tools/generate_repository_artifacts.py. Do not edit by hand. -->

Run repository validation from the repository root:

```powershell
python .\tools\validate_skill_manifest.py
python .\tools\test_skill_manifest.py
python .\tools\generate_repository_artifacts.py --check
python .\tools\test_generate_repository_artifacts.py
python .\tools\validate_provenance.py
python .\tools\test_deep_planning_validator.py
python .\tools\test_office_com_contract.py
python .\tools\test_visual_runtime_contract.py
python .\tools\test_visual_skills_contract.py
python .\tools\validate_codex_hooks.py
node --test document-handoff/scripts/tests/*.test.mjs
```

The repository CI also runs PSScriptAnalyzer, PowerShell parser checks, Python compile checks, metadata tests, and repository contract checks. Environment-dependent Microsoft Office smoke tests remain explicit and are not hosted CI gates.
<!-- END GENERATED: validation-summary -->

## Codex hooks

The repository includes `.codex/hooks.json`. The hook integration is warning-only: failures are surfaced but do not block execution. Validate it with `python .\tools\validate_codex_hooks.py`.

## Design workflow

The Codex visual skills share a `render-inspect-lint-revise` workflow through `.shared/visual-runtime`. The shared runtime produces screenshots, console output, artifact metadata, and QA evidence for review.
