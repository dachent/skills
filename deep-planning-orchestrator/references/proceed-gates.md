# Proceed Gates

Proceed gates prevent planning drift and accidental execution.

## Gate Rules

- Stop after each major phase when the status is `READY_FOR_PROCEED`.
- Ask for explicit `PROCEED` or a direct equivalent.
- If the user changes requirements at a gate, update criteria and revisit affected phases.
- If the user asks to execute while required artifacts are missing, state the missing artifacts and continue planning.

## Gate Message Shape

Use this concise form:

```text
Phase N is ready.
Artifacts: ...
Status: READY_FOR_PROCEED.
Next after PROCEED: ...
```

Do not hide blockers inside a ready message.

## Major Handoff Gates

Run or update handoff at:

- after Phase 0 criteria are locked;
- after failure autopsy if one exists;
- after final plan approval;
- before execution handoff;
- at final archive.

If `$handoff` is unavailable, write a concise handoff under `.deep-planning/handoffs/`.
