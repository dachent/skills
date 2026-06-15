# Project Modes

Select the mode during harness preflight. If multiple modes fit, choose the one with the strictest delivery constraints.

## software-git

Use when:

- a `.git/` directory or Git worktree is present;
- the user permits commits, branches, PRs, or CI;
- code changes are the main deliverable.

Required controls:

- record branch, status, recent commits, remote if available;
- define commit or PR boundaries;
- use CI or local test commands as validation surfaces;
- rollback by revert or follow-up commit, never destructive reset without explicit approval.

## software-no-git

Use when:

- code, scripts, notebooks, configs, or automation are involved;
- no Git workflow is available or commits are out of scope.

Required controls:

- record allowed write scope;
- snapshot files before implementation;
- maintain changed-file summaries;
- validate with commands or manual checks;
- rollback by restoring snapshots.

## business-artifact

Use when:

- deliverables are documents, spreadsheets, reports, memos, dashboards, decisions, or analysis;
- code is absent or incidental.

Required controls:

- identify stakeholders and approvers;
- catalog source-of-truth materials;
- define acceptance checks and evidence;
- maintain decision log and final approval packet;
- rollback by preserving prior artifact versions.

## mixed-business-coding

Use when:

- business deliverables depend on code, scripts, data transforms, notebooks, or automation;
- there may be no commit workflow.

Required controls:

- combine business source catalog with code/script inventory;
- snapshot code and artifacts before execution;
- validate both technical outputs and business acceptance;
- record changed files, changed artifacts, and evidence.

Default to this mode when uncertain.
