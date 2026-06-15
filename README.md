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

## Skill Catalog

| Skill | Engine | Upstream source | Smoke test |
| --- | --- | --- | --- |
| [`adversarial-plan-review-codex`](./adversarial-plan-review-codex) | Codex hostile plan review | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live flawed-plan fixture plus repo metadata validation |
| [`deep-planning-codex`](./deep-planning-codex) | Codex-native gated planning workflow | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live subagent forward-tests plus artifact validator |
| [`docx-win`](./docx-win) | Microsoft Word COM + PowerShell | `anthropics/skills` -> `skills/docx` | `powershell -ExecutionPolicy Bypass -File .\docx-win\scripts\smoke-test.ps1` |
| [`grill-me-codex`](./grill-me-codex) | Codex read-only design interview | `mattpocock/skills` -> `skills/productivity/grill-me` | Live interview scenario tests plus repo metadata validation |
| [`grill-with-docs-codex`](./grill-with-docs-codex) | Codex docs-backed design interview | `mattpocock/skills` -> `skills/engineering/grill-with-docs` | Live docs fixture tests plus repo metadata validation |
| [`handoff-codex`](./handoff-codex) | Codex continuation document workflow | `mattpocock/skills` -> `skills/productivity/handoff` | Temp-file handoff scenario plus repo metadata validation |
| [`pptx-win`](./pptx-win) | Microsoft PowerPoint COM + PowerShell, OOXML fallback | `anthropics/skills` -> `skills/pptx` | `powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\smoke_test.ps1` |
| [`repo-map-codex`](./repo-map-codex) | Codex project and evidence mapping | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live mixed-project fixture plus repo metadata validation |
| [`xlsx-win`](./xlsx-win) | Microsoft Excel COM + PowerShell, Python helpers | `anthropics/skills` -> `skills/xlsx` | `powershell -ExecutionPolicy Bypass -File .\xlsx-win\scripts\self_test_xlsx_win.ps1` |
| [`ultraplan-codex`](./ultraplan-codex) | Codex-native deep implementation planning workflow | `6missedcalls/ultraplan` -> `.` | Live subagent forward-tests plus repo metadata validation |
| [`verification-plan-codex`](./verification-plan-codex) | Codex proof and rollback planning | `dachent/cdc05151d047708c290bd4da0aaeed96` -> `deep_planning.txt` | Live verification fixture plus Python artifact validation |

## Prerequisites

- Codex or Claude configured to load local skills from your skills directory
- For `docx-win`, `pptx-win`, and `xlsx-win`: Windows with a local interactive desktop session
- For `docx-win`, `pptx-win`, and `xlsx-win`: Microsoft 365 desktop apps installed for the relevant skill
- PowerShell for the Office automation entrypoints and repo validation scripts
- Python 3 for the bundled Python helpers and repo tooling
- For `ultraplan-codex`: a Codex session that can read the target codebase and write `.ultraplan/plan.md`
- For `grill-me-codex`: a Codex session that can read the target codebase or artifacts before asking the user discoverable questions
- For `grill-with-docs-codex`: permission to update project documentation such as `CONTEXT.md` and accepted ADRs
- For `handoff-codex`: permission to write a redacted continuation document to the operating system temporary directory
- For the Codex deep planning suite: permission to create or update `.deep-planning/` planning artifacts in the target project, and optionally `.ultraplan/plan.md` when `ultraplan-codex` is part of the selected workflow

## Installation

### Codex

1. Clone this repository locally.
2. Copy the shared runtime folder `.shared\office-com` and the skill folders you want to use into your Codex skills directory, for example `%USERPROFILE%\.codex\skills\`.
3. Keep the directory names unchanged: `.shared`, `adversarial-plan-review-codex`, `deep-planning-codex`, `docx-win`, `grill-me-codex`, `grill-with-docs-codex`, `handoff-codex`, `pptx-win`, `repo-map-codex`, `ultraplan-codex`, `verification-plan-codex`, and `xlsx-win`.
4. Use the skill by name from Codex, for example `$deep-planning-codex`, `$repo-map-codex`, `$verification-plan-codex`, `$adversarial-plan-review-codex`, `$docx-win`, `$grill-me-codex`, `$grill-with-docs-codex`, `$handoff-codex`, `$pptx-win`, `$ultraplan-codex`, or `$xlsx-win`.
5. Before relying on Excel, PowerPoint, or Word COM from a new machine or session, run the shared preflight from a signed-in desktop-user PowerShell window:

   ```powershell
   & "$env:USERPROFILE\.codex\skills\.shared\office-com\scripts\office_com_preflight.ps1" -Apps @('Excel','PowerPoint','Word')
   ```

6. Run the relevant smoke test or live validation before relying on a new machine or session.

### Claude Code

1. Clone this repository locally.
2. In your project's `.claude/skills/` directory, copy or symlink the desired subdirectories from `.claude/skills/` in this repository: `docx-win`, `pptx-win`, and `xlsx-win`.
3. If you plan to use the Office skills, also copy the shared runtime folder `.shared\office-com` from this repository into `.claude\skills\.shared\office-com` so the skill wrappers can resolve their shared preflight module.
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
python .\tools\test_deep_planning_validator.py
$compilePaths = @('.\tools')
$compilePaths += Get-ChildItem -Path . -Directory -Recurse -Filter scripts | ForEach-Object { $_.FullName }
python -m compileall -q @compilePaths
```

## Repo Layout

- [`.shared/office-com/`](./.shared/office-com): shared Office COM preflight and guard runtime used by Excel, PowerPoint, and Word wrappers
- [`adversarial-plan-review-codex/`](./adversarial-plan-review-codex): Codex hostile review skill for execution plans
- [`deep-planning-codex/`](./deep-planning-codex): master Codex deep planning workflow skill
- [`docx-win/`](./docx-win): Word skill, scripts, references, and agent metadata
- [`grill-me-codex/`](./grill-me-codex): read-only plan and design grilling interview skill adapted from `mattpocock/skills`
- [`grill-with-docs-codex/`](./grill-with-docs-codex): docs-backed plan grilling skill with context and ADR references adapted from `mattpocock/skills`
- [`handoff-codex/`](./handoff-codex): redacted continuation handoff skill adapted from `mattpocock/skills`
- [`pptx-win/`](./pptx-win): PowerPoint skill, scripts, references, fallback OOXML utilities, and agent metadata
- [`repo-map-codex/`](./repo-map-codex): Codex project map and evidence catalog skill
- [`ultraplan-codex/`](./ultraplan-codex): Codex-native deep implementation planning skill adapted from `6missedcalls/ultraplan`
- [`verification-plan-codex/`](./verification-plan-codex): Codex proof criteria and rollback planning skill
- [`xlsx-win/`](./xlsx-win): Excel skill, scripts, references, and agent metadata
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
- run the hosted validation commands locally before opening a PR
- request the Office smoke workflow when a change affects runtime Office automation behavior

## Licensing And Provenance

This repository records provenance for each skill but does not currently publish a root `LICENSE` file.

Before redistributing or repackaging this repository, review the upstream provenance and decide on an explicit licensing policy for the repo as a whole.

Current upstream provenance:

| Skill | Upstream repo | Source folder | Source branch | Port depth |
| --- | --- | --- | --- | --- |
| `adversarial-plan-review-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `deep-planning-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `docx-win` | `https://github.com/anthropics/skills` | `skills/docx` | `main` | Light port |
| `grill-me-codex` | `https://github.com/mattpocock/skills` | `skills/productivity/grill-me` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Light Codex adaptation |
| `grill-with-docs-codex` | `https://github.com/mattpocock/skills` | `skills/engineering/grill-with-docs` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Medium Codex adaptation |
| `handoff-codex` | `https://github.com/mattpocock/skills` | `skills/productivity/handoff` | `main` at `694fa30311e02c2639942308513555e61ee84a6f` (`2026-06-10 16:01:44 +0100`) | Light Codex adaptation |
| `pptx-win` | `https://github.com/anthropics/skills` | `skills/pptx` | `main` | Light port |
| `repo-map-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `ultraplan-codex` | `https://github.com/6missedcalls/ultraplan` | `.` | `main` at `06779940475f9c52b4d3b546d309b2c31ebbf8ea` (`2026-03-31T21:48:42Z`) | Heavy Codex adaptation |
| `verification-plan-codex` | `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96` | `deep_planning.txt` | HEAD at `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83` | New Codex-native derivative |
| `xlsx-win` | `https://github.com/anthropics/skills` | `skills/xlsx` | `main` | Heavy adaptation |
