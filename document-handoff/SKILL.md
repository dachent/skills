---
name: document-handoff
description: Create a comprehensive project handoff package — workfolder copy + dark-mode HTML memo — from any Claude Code, Codex, or OpenCode project. Run at any project milestone.
---

# document-handoff

Produce a self-contained handoff package: a curated workfolder copy of project files plus a dark-mode HTML memo covering 16 structured sections. Enables any agent to cold-start on the project without re-reading sessions.

**Announce at start:** "I'm using the document-handoff skill to create a project handoff package."

---

## Prerequisites

Resolve the CLI path once at session start:

```powershell
$cli = (Get-ChildItem "$env:USERPROFILE\.claude\plugins\cache" -Recurse -Filter "cli.mjs" -ErrorAction SilentlyContinue |
  Where-Object { $_.FullName -match [regex]::Escape("document-handoff\scripts") } |
  Select-Object -First 1).FullName

if (-not $cli) {
  # Fallback: check Codex and OpenCode plugin caches
  $cli = (Get-ChildItem "$env:USERPROFILE\.codex\plugins" -Recurse -Filter "cli.mjs" -ErrorAction SilentlyContinue |
    Where-Object { $_.FullName -match [regex]::Escape("document-handoff\scripts") } |
    Select-Object -First 1).FullName
}
if (-not $cli) { Write-Error "document-handoff cli.mjs not found in plugin cache"; return }
```

---

## Collect Inputs

Ask the user (or infer from context):

1. **Project slug** — short name used in output file names (e.g. `my-project`)
2. **Source root** — absolute path to the project directory to archive
3. **Output directory** — where to write the workfolder and memo (default: `<source_root>\.handoff-output`)
4. **Fresh or resume?** — `--fresh` overwrites existing state; `--resume` continues from last completed phase

**Provider detection note:** The skill auto-detects whether you are running under Claude Code, Codex, or OpenCode via environment variables. No user action needed.

```powershell
$slug = "<project-slug>"
$sourceRoot = "<absolute-path-to-project>"
$outputDir = "$sourceRoot\.handoff-output"
$statePath = "$outputDir\.handoff\state.json"
```

---

## Phase 0 — Initialize

```powershell
node --no-warnings $cli init --project $slug --source-root $sourceRoot --output-dir $outputDir --fresh
```

---

## Phase 1 — Discover

```powershell
node --no-warnings $cli discover --state $statePath
```

**GATE:** Review `$outputDir\.handoff\catalog.html` in a browser. For each high-risk file listed as excluded:
- If you need it: open `$outputDir\.handoff\catalog.json`, set `"action": "copy"` on that entry, save.
- If excluded files are correct: proceed.

Type **PROCEED** to continue.

---

## Phase 2 — Populate

```powershell
node --no-warnings $cli populate --state $statePath
```

---

## Phase 3 — Extract Sessions

```powershell
node --no-warnings $cli extract-sessions --state $statePath
```

**GATE:** Review the sessions listed above. Confirm these are the right sessions for this project.

If sessions are missing: they may not have a matching `cwd` in their metadata. You can manually add session entries to `$statePath` under `sessions_found`.

Type **PROCEED** and set `sessions_validated: true` in state, or edit state manually.

---

## Phase 4 — Synthesize

```powershell
node --no-warnings $cli synthesize --state $statePath
```

---

## Phase 5 — Sections (GATE — no script)

Review `$outputDir\.handoff\synthesis.md`. The skill will write these 16 sections:

bootstrap, executive-summary, deliverables, current-state, technical-decisions, challenges-blockers, next-steps, context-sources, open-questions, dependencies, environment, testing, architecture, data-flow, changelog

Plus `privacy-security` if any risk-flagged files were found.

**GATE:** Confirm the section list or remove any sections you don't need.

Type **PROCEED** to render.

---

## Phase 6 — Render Memo

```powershell
node --no-warnings $cli render-memo --state $statePath
```

Open `$outputDir\$slug-memo.html` in a browser to preview.

---

## Phase 7 — Verify

```powershell
node --no-warnings $cli verify --state $statePath
```

Review `$outputDir\.handoff\verification.json`. If `overall: false`, fix the reported issues and re-run this phase.

---

## Outputs

| File | Description |
|---|---|
| `$outputDir\$slug-memo.html` | Dark-mode HTML handoff memo (16 sections) |
| `$outputDir\$slug-agent-context.json` | Agent cold-start context with citation index |
| `$outputDir\.handoff\catalog.json` | Full file inventory with risk flags |
| `$outputDir\.handoff\catalog.html` | Visual catalog browser |
| `$outputDir\.handoff\digests.json` | Session digests |
| `$outputDir\.handoff\synthesis.md` | Synthesis narrative |
| `$outputDir\.handoff\verification.json` | Verification results |
| `$outputDir\.handoff\{slug}-citation-index.json` | Citation graph |
| `$outputDir\plans\`, `code\`, `artifacts\`, `inputs\` | Curated workfolder |
