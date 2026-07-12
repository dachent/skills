# LLM agent skills

[![Validate](https://github.com/dachent/skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dachent/skills/actions/workflows/validate.yml)

Focused Codex and Claude skills for Office automation, visual artifacts, implementation planning, code analysis, interviews, and project handoff.

`skills-manifest.json` is the canonical inventory for supported skills, ownership, platform and agent support, source classification, and validation commands. See [`docs/repository-contract.md`](./docs/repository-contract.md) for integration requirements.

## Why this repository exists

The repository began with Windows Office skills adapted into native Microsoft Word, PowerPoint, and Excel COM workflows. It now also contains browser-visual tooling, gated planning workflows, repository and dependency analysis, structured interviews, and durable project handoff tooling.

The Office skills remain intentionally Windows-specific and environment-dependent. Browser, planning, handoff, and code-analysis skills declare their own platform and runtime boundaries in the manifest.

## Skill catalog

| Skill | Family | Purpose | Primary validation |
| --- | --- | --- | --- |
| [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | Planning | Hostile review of plans before implementation | Deep-planning validator |
| [`artifact-runtime-codex`](./artifact-runtime-codex) | Visual | Runtime and evidence handoff for browser artifacts | Visual-skill contracts |
| [`canvas-design-codex`](./canvas-design-codex) | Visual | Canvas, SVG, WebGL, and pixel-evidence QA | Visual-skill contracts |
| [`code-mapper-skill`](./code-mapper-skill) | Code analysis | Python dependency, symbol, artifact, and contract mapping | Self-test and smoke suite |
| [`deep-planning-codex`](./deep-planning-codex) | Planning | Gated, evidence-backed implementation planning | Deep-planning validator |
| [`document-handoff`](./document-handoff) | Handoff | Curated project workfolder and browsable HTML memo | Provider and extraction tests |
| [`docx-win`](./docx-win) | Office | Word COM automation and no-template document polish | Static contract plus Office smoke |
| [`frontend-design-codex`](./frontend-design-codex) | Visual | Responsive frontend design with screenshot QA | Visual-skill contracts |
| [`grill-me-codex`](./grill-me-codex) | Interview | Read-only design and plan interrogation | Scenario validation |
| [`grill-with-docs-codex`](./grill-with-docs-codex) | Interview | Documentation-backed design interview and ADR workflow | Scenario validation |
| [`handoff-codex`](./handoff-codex) | Handoff | Redacted continuation handoff document | Scenario validation |
| [`pptx-win`](./pptx-win) | Office | PowerPoint COM automation and no-template deck QA | Static contract plus Office smoke |
| [`repo-map-codex`](./repo-map-codex) | Planning | Project structure and evidence mapping | Deep-planning validator |
| [`theme-factory-codex`](./theme-factory-codex) | Visual | Design tokens, palettes, and theme QA | Visual-skill contracts |
| [`ultraplan-codex`](./ultraplan-codex) | Planning | Deep implementation planning for complex work | Live planning scenarios |
| [`verification-plan-codex`](./verification-plan-codex) | Planning | Success criteria, proof, rollback, and recovery planning | Deep-planning validator |
| [`web-artifacts-builder-codex`](./web-artifacts-builder-codex) | Visual | Standalone web artifact creation and evidence packaging | Visual-skill contracts |
| [`xlsx-win`](./xlsx-win) | Office | Excel COM refresh, calculation, and workbook reliability | Static contract plus Office smoke |

## Prerequisites

Common repository tooling:

- Python 3.12 for hosted validation and bundled Python helpers;
- Node.js 20 and npm for the visual runtime and `document-handoff` tests;
- PowerShell 7 for repository and Office automation validation;
- Codex or Claude Code configured to load local skills.

Skill-specific requirements:

- `docx-win`, `pptx-win`, and `xlsx-win` require Windows, an interactive signed-in desktop session, and the corresponding Microsoft 365 desktop application;
- `code-mapper-skill` uses `grimp` and `jedi`; Git URL targets additionally require Git;
- `document-handoff` currently supports Claude Code and Codex session discovery. OpenCode extraction is not implemented;
- planning skills require permission to write their declared planning artifacts, such as `.deep-planning/` or `.ultraplan/`.

## Installation

### Codex

1. Clone this repository.
2. Copy the desired top-level skill directories into the Codex skills directory, commonly `%USERPROFILE%\.codex\skills\`.
3. Copy required shared runtimes:
   - `.shared\office-com` for Office skills;
   - `.shared\visual-runtime` for browser-visual skills.
4. Keep directory names unchanged.
5. Run the relevant hosted or environment-dependent validation before relying on a new machine.

### Claude Code

Use the canonical top-level skill directories unless an explicitly generated agent mirror is introduced. The existing `.claude/skills` Office copies are legacy mirrors and are not the canonical source of behavior.

For Office skills, also copy `.shared\office-com` into the installed skills tree so wrappers can resolve the shared preflight module.

## Validation and CI

Hosted validation fans out into three independently visible jobs:

- **Repository integrity**: canonical inventory, metadata and path references, provenance, hooks, and agent definitions;
- **Static and contract checks**: PowerShell analysis, Python compilation, Office boundaries, and visual-runtime contracts;
- **Behavioral tests**: code-mapper self-tests and smoke tests, document-handoff provider tests, and deep-planning validation.

A stable **Required** aggregation job is intended for branch protection. Pull-request runs use concurrency cancellation so superseded commits do not consume validation capacity.

The [`.codex/agents`](./.codex/agents) prompts support visual QA, artifact packaging, accessibility review, and Office evidence review. [`.codex/hooks.json`](./.codex/hooks.json) contains warning-only reminders for visual QA, PowerPoint rendering, provenance review, accessibility, and Office COM boundary honesty. `tools/validate_codex_hooks.py` validates these contracts. No hook instantiates Office COM.

True Office runtime validation remains separate because GitHub-hosted runners do not provide reliable Microsoft Office COM automation. `.github/workflows/office-smoke.yml` runs Word, PowerPoint, and Excel smoke tests on a self-hosted Windows runner labeled `office` and uploads logs and generated artifacts.

Local hosted-equivalent commands include:

```powershell
python .\tools\validate_skill_manifest.py
python .\tools\test_skill_manifest.py
pwsh -NoLogo -NoProfile -File .\tools\validate_repo.ps1
pwsh -NoLogo -NoProfile -File .\tools\validate_powershell.ps1 -SettingsPath .github\PSScriptAnalyzerSettings.psd1
python .\tools\validate_provenance.py
python .\tools\test_deep_planning_validator.py
python .\tools\test_office_com_contract.py
python .\tools\test_visual_runtime_contract.py
python .\tools\test_visual_skills_contract.py
python .\tools\validate_codex_hooks.py
python -m pip install -r .\code-mapper-skill\scripts\requirements.txt
python .\code-mapper-skill\tests\selftest.py
python .\code-mapper-skill\scripts\smoke_test.py
node --test document-handoff/tests/providers.test.mjs
```

## Repository layout

- [`skills-manifest.json`](./skills-manifest.json): canonical inventory and integration metadata;
- [`docs/repository-contract.md`](./docs/repository-contract.md): required packaging and maintenance rules;
- [`.upstream/`](./.upstream): pinned Office upstream snapshots and drift reports;
- [`.shared/office-com/`](./.shared/office-com): shared Office preflight and COM boundary runtime;
- [`.shared/visual-runtime/`](./.shared/visual-runtime): browser screenshot, lint, PDF, and image-evidence tooling;
- [`.codex/agents`](./.codex/agents): visual critic, builder, packager, accessibility, and Office evidence-review agents;
- [`.codex/hooks.json`](./.codex/hooks.json): warning-only reminders for visual QA, rendering, provenance, accessibility, and COM boundaries;
- each top-level skill directory: canonical skill definition, scripts, references, tests, and agent metadata as applicable;
- [`.github/workflows/`](./.github/workflows): hosted validation, upstream drift, and self-hosted Office smoke workflows;
- [`tools/`](./tools): repository validators and contract tests.

## Provenance and licensing

The manifest records a source classification for every supported skill. Office-derived skills retain pinned Anthropic source snapshots and dedicated provenance files. `code-mapper-skill` and `document-handoff` now have explicit provenance records; the latter records that the original imported source and license remain unresolved.

The repository does not currently publish a root `LICENSE`. Do not assume redistribution rights for the repository as a whole. Review each upstream license and resolve the root licensing policy before repackaging or redistribution.

## Contributing

A supported skill must remain registered in `skills-manifest.json` and provide the packaging declared there. Adding an unregistered top-level `SKILL.md` directory or omitting required agent metadata fails hosted validation.

Use the pull-request checklist. Keep support claims aligned with implemented behavior, add behavioral tests where practical, document environment-dependent tests explicitly, and avoid undeclared machine-specific paths.
