---
name: document-handoff
description: Use when a project is complete and you need to produce a structured handoff package — an organized workfolder plus a browsable HTML memo — so any future agent or human can reconstruct the project cold. Use when: concluding a multi-session AI or dev project, archiving Claude Code or Codex sessions, preparing knowledge transfer documentation, parking a project long-term.
---

# Document Handoff

Produce a structured workfolder and browsable dark-mode HTML memo for a completed project.

Follow these phases in exact order. **Never skip a phase. Never auto-advance past a GATE.**

---

## Collect Inputs

Ask the user for all three before doing anything else:

1. **Project slug** — short identifier, prefix for all output files (e.g. `weekly-emr-extract`). Lowercase, hyphens only.
2. **Source root** — full path to directory with original session files, code, artifacts, plans.
3. **Output directory** — full path where the workfolder should be written.

---

## Check for Existing Run

Before starting, check for `{output_dir}\.handoff\state.json`.

If it **exists**: read it and show the user:
```
Project: {project}
Phases completed: {phases_completed}
Created: {created_at}
```
Ask: **Resume** (skip completed phases) or **Fresh** (delete `.handoff\` and rebuild)?

If Fresh:
```powershell
Remove-Item -Path "{output_dir}\.handoff" -Recurse -Force
```

---

## Create Workfolder Structure

Initializes the capsule directory tree. All project files are copied here in Phase 1.5 — the workfolder is the self-contained record. Run once (skip if resuming and dirs already exist):

```powershell
$base = "{output_dir}"
@('code\src','code\tests','code\config','artifacts','logs\codex','logs\claude',
  'plans','memory','inputs','deprecated','.handoff\tmp') | ForEach-Object {
  New-Item -ItemType Directory -Path (Join-Path $base $_) -Force | Out-Null
}
```

Write `{output_dir}\.handoff\state.json` (replace placeholders with actual values):
```json
{
  "project": "{slug}",
  "source_root": "{source_root}",
  "output_dir": "{output_dir}",
  "created_at": "{ISO-8601-timestamp}",
  "phases_completed": [],
  "file_inventory": [],
  "catalog_path": "",
  "digests_path": "",
  "synthesis_path": "",
  "approved_sections": [],
  "memo_path": "",
  "verified": false
}
```

Write `{output_dir}\deprecated\_excluded.md`:
```markdown
# Excluded Files

No deprecated files identified during this handoff run.
```

---

## Phase 1 — Discovery

Skip if `phases_completed` contains `"discovery"`.

```
Workflow({ scriptPath: "C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\scripts\\01-discovery.js", args: { project: "{slug}", source_root: "{source_root}", output_dir: "{output_dir}" } })
```

After completion, update `state.json`: set `catalog_path`, `file_inventory`, append `"discovery"` to `phases_completed`.

Show the user:
- Total files found
- Breakdown by directory (name, file count, size)
- Path to `{project}-catalog.html`

**GATE:** Ask: "Does this catalog look correct? Reply 'yes' to proceed to population, or describe what's missing." Do not proceed until explicit approval.

---

## Phase 1.5 — Population

Skip if `phases_completed` contains `"population"`.

```
Workflow({ scriptPath: "C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\scripts\\03-population.js", args: { project: "{slug}", source_root: "{source_root}", output_dir: "{output_dir}", state: {state_object} } })
```

After completion, update `state.json`: set `references_path` = `{output_dir}\inputs\REFERENCES.md`, append `"population"` to `phases_completed`.

Show the user:
- Files copied into workfolder: {files_copied}
- Baseline inputs referenced (not copied): {files_referenced}
- Reference manifest: `{output_dir}\inputs\REFERENCES.md`

---

## Phase 2 — Synthesis

Skip if `phases_completed` contains `"synthesis"`.

When `"population"` is in `phases_completed`, synthesis reads files from the workfolder capsule instead of `source_root`.

```
Workflow({ scriptPath: "C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\scripts\\02-synthesis.js", args: { project: "{slug}", source_root: "{source_root}", output_dir: "{output_dir}", state: {state_object} } })
```

After completion, update `state.json`: set `digests_path`, `synthesis_path`, append `"synthesis"` to `phases_completed`.

Show the user:
- Session logs digested / doc files digested
- Key decisions count
- Challenges count (SEEDED vs DISCOVERED breakdown)
- Path to `{project}-synthesis.md`

**GATE:** Ask: "Does this synthesis look complete? Reply 'yes' to proceed to section planning, or describe gaps." Do not proceed until explicit approval.

---

## Phase 3 — Section Recommendation

Skip if `phases_completed` contains `"sections"`.

Read `{synthesis_path}` and `{digests_path}`.

**Baseline sections** (always start from this list):
`#overview`, `#flow`, `#scope`, `#state`, `#runbook`, `#modules`, `#tests`, `#decisions`, `#missed`, `#challenges`, `#config`, `#improvements`, `#productionize`, `#catalog`

Compare project content against baseline. Recommend:
- **Add** sections with rationale (e.g. project has a database schema → add `#schema`)
- **Remove or mark N/A** with rationale (e.g. no test suite → note `#tests` will document the gap, not be omitted)
- **Keep** all others

Present recommendation. Wait for user to approve final section list.

After approval, update `state.json`: set `approved_sections`, append `"sections"` to `phases_completed`.

---

## Phase 4 — Memo Generation

Skip if `phases_completed` contains `"memo"`.

Run section writers:
```
Workflow({ scriptPath: "C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\scripts\\04-section-writers.js", args: { project: "{slug}", output_dir: "{output_dir}", state: {state_object} } })
```

After all agents complete, assemble fragments:
```powershell
powershell -ExecutionPolicy Bypass -File "C:\Users\BorisVaisman\.claude\skills\document-handoff\scripts\assemble-memo.ps1" -ProjectSlug "{slug}" -OutputDir "{output_dir}"
```

Update `state.json`: set `memo_path` = `{output_dir}\{slug}-memo.html`, append `"memo"` to `phases_completed`.

---

## Phase 5 — Verification

```
Workflow({ scriptPath: "C:\\Users\\BorisVaisman\\.claude\\skills\\document-handoff\\scripts\\05-verification.js", args: { project: "{slug}", output_dir: "{output_dir}", state: {state_object} } })
```

Interpret results:
- `stage: 1, passed: false` → Show exact failing check. Stop. Ask how to fix.
- `stage: 2, passed: false` → Show each QC failure (section + axis + specific issue). Stop. Ask how to fix.
- QC warnings → Surface to user. Let user decide to fix or accept.
- `stage: 3` blockers → Stop. Show visual issues.
- `stage: 3` warnings → Surface. User decides.

If all clear, open memo in browser:
```
mcp__Claude_in_Chrome__navigate({ url: "file:///{memo_path_forward_slashes}" })
```

Tell the user: "The memo is open in your browser. Please review it and reply 'approved' when satisfied."

**GATE:** Wait for explicit user approval. After approval:
- Update `state.json`: set `verified: true`, append `"verification"` to `phases_completed`

Summarize deliverables:
- `{slug}-catalog.html` — file inventory
- `{slug}-digests.json` — structured session digests
- `{slug}-synthesis.md` — narrative synthesis
- `{slug}-memo.html` — primary handoff document ✓ verified
