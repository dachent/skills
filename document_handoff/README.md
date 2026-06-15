# document-handoff Skill

Claude Code skill that converts a completed AI/dev project into a structured handoff package:
a file catalog, synthesis document, and a browsable dark-mode HTML memo.

## Install

```powershell
.\install.ps1
```

Copies skill files to `~/.claude/skills/document-handoff/`. Run any time after editing source files here to update the installed version.

## Update

Edit files in this folder, then run `.\install.ps1` again.

## Use

In Claude Code, type `/document-handoff`. Provide:
1. Project slug (lowercase, hyphens only)
2. Source root (path to session logs, code, artifacts, plans)
3. Output directory (where workfolder will be written)

## Output

- `{slug}-catalog.html` — file inventory
- `{slug}-digests.json` — structured session digests
- `{slug}-synthesis.md` — narrative synthesis
- `{slug}-memo.html` — primary handoff memo (dark mode, sidebar nav)

## Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Orchestration instructions for Claude |
| `scripts/01-discovery.js` | Workflow: parallel directory scanners → catalog HTML |
| `scripts/02-synthesis.js` | Workflow: session extraction + digest agents → synthesis |
| `scripts/04-section-writers.js` | Workflow: parallel section agents → HTML fragments |
| `scripts/05-verification.js` | Workflow: structural + QC + Chrome visual verification |
| `scripts/assemble-memo.ps1` | PowerShell: concatenate fragments → memo HTML |
| `templates/css-dark.html` | Dark mode CSS + sidebar scroll-spy JS |
