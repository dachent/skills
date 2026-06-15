# Rollback And Recovery

## Git

- Prefer revert or follow-up commits.
- Never destructive reset without explicit user approval.
- Record commit or branch to recover from.

## No-Git Code

- Snapshot files before edits.
- Record snapshot path and timestamp.
- Restore snapshots for rollback.

## Business Artifacts

- Preserve prior versions.
- Keep source materials unchanged.
- Record how generated outputs can be recreated.

## Mixed Work

- Restore code snapshots and regenerate business artifacts from unchanged sources.
- If manual edits cannot be regenerated, preserve a copy before editing.
