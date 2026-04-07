# llm agent skills

[![Validate](https://github.com/dachent/codex_skills/actions/workflows/validate.yml/badge.svg?branch=main)](https://github.com/dachent/codex_skills/actions/workflows/validate.yml)

Windows-native skills for Word, PowerPoint, and Excel using Microsoft Office COM automation.

Canonical GitHub About settings:
- Description: `Windows-native Codex skills for Word, PowerPoint, and Excel using Microsoft Office COM automation.`
- Topics: `codex`, `skills`, `windows`, `powershell`, `python`, `microsoft-office`, `office-automation`, `word`, `powerpoint`, `excel`, `com-automation`
- Homepage: leave blank until the repository has a real external docs or project site

## Why This Repo Exists

This repository ports Office-oriented skills from Anthropic's `skills` repository into Codex-friendly Windows workflows.

The core design choice is deliberate: prefer local Microsoft Office desktop automation over LibreOffice-style file transformation whenever Word, PowerPoint, or Excel fidelity matters. That makes these skills Windows-specific and environment-dependent by design.

## Skill Catalog

| Skill | Engine | Upstream source | Smoke test |
| --- | --- | --- | --- |
| [`docx-win`](./docx-win) | Microsoft Word COM + PowerShell | `anthropics/skills` -> `skills/docx` | `powershell -ExecutionPolicy Bypass -File .\docx-win\scripts\smoke-test.ps1` |
| [`pptx-win`](./pptx-win) | Microsoft PowerPoint COM + PowerShell, OOXML fallback | `anthropics/skills` -> `skills/pptx` | `powershell -ExecutionPolicy Bypass -File .\pptx-win\scripts\smoke_test.ps1` |
| [`xlsx-win`](./xlsx-win) | Microsoft Excel COM + PowerShell, Python helpers | `anthropics/skills` -> `skills/xlsx` | `powershell -ExecutionPolicy Bypass -File .\xlsx-win\scripts\self_test_xlsx_win.ps1` |

## Prerequisites

- Windows with a local interactive desktop session
- Microsoft 365 desktop apps installed for the skills you plan to use
- PowerShell for the Office automation entrypoints
- Python 3 for the bundled Python helpers and fallback tooling
- Codex configured to load local skills from your skills directory

## Installation

### Codex

1. Clone this repository locally.
2. Copy the skill folders you want to use into your Codex skills directory, for example `%USERPROFILE%\.codex\skills\`.
3. Keep the directory names unchanged: `docx-win`, `pptx-win`, and `xlsx-win`.
4. Use the skill by name from Codex, for example `$docx-win`, `$pptx-win`, or `$xlsx-win`.
5. Run the relevant smoke test before relying on a new machine or Office installation.

### Claude Code

1. Clone this repository locally.
2. In your project's `.claude/skills/` directory, copy or symlink the three subdirectories from `.claude/skills/` in this repository: `docx-win`, `pptx-win`, and `xlsx-win`.
3. Keep the directory names unchanged.
4. Reference each skill from a `CLAUDE.md` or system prompt by its name, for example `docx-win`, `pptx-win`, or `xlsx-win`.
5. Run the relevant smoke test before relying on a new machine or Office installation.

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

Local validation commands:

```powershell
pwsh -NoLogo -NoProfile -File .\tools\validate_repo.ps1
pwsh -NoLogo -NoProfile -File .\tools\validate_powershell.ps1 -SettingsPath .github\PSScriptAnalyzerSettings.psd1
python -m compileall -q .\pptx-win\scripts .\xlsx-win\scripts .\tools
```

## Repo Layout

- [`docx-win/`](./docx-win): Word skill, scripts, references, and agent metadata
- [`pptx-win/`](./pptx-win): PowerPoint skill, scripts, references, fallback OOXML utilities, and agent metadata
- [`xlsx-win/`](./xlsx-win): Excel skill, scripts, references, and agent metadata
- [`.github/workflows/`](./.github/workflows): hosted validation and self-hosted Office smoke workflows
- [`tools/`](./tools): repository validation helpers used by CI and local contributors

## Contributing

Contributions should preserve the repo's current contract:

- keep each skill Windows-specific and COM-first unless the skill explicitly documents a fallback path
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
| `docx-win` | `https://github.com/anthropics/skills` | `skills/docx` | `main` | Light port |
| `pptx-win` | `https://github.com/anthropics/skills` | `skills/pptx` | `main` | Light port |
| `xlsx-win` | `https://github.com/anthropics/skills` | `skills/xlsx` | `main` | Heavy adaptation |
