# Phase Contracts

Every phase must update `.deep-planning/state.md` and end with one status:

- `READY_FOR_PROCEED`: phase artifact exists and no blocking issue remains.
- `BLOCKED_NEEDS_USER_DECISION`: a non-discoverable decision is required.
- `BLOCKED_BY_MISSING_EVIDENCE`: required source material, access, or repro evidence is missing.
- `FAILED_VALIDATION`: artifact is inconsistent, incomplete, or contradicted by evidence.

## Required State Fields

Each state update must include:

- current phase;
- project mode;
- status;
- artifacts created or updated;
- key decisions;
- unresolved assumptions;
- next action after `PROCEED`.

## Phase Completion Rules

- Do not mark a phase ready if required artifacts are missing.
- Do not carry hidden assumptions forward. Put them in `assumption-ledger.md`.
- Do not ask the user for discoverable facts.
- Do not skip targeted probes when an unverified assumption could invalidate the plan.
- Do not proceed to final execution planning until verification and adversarial review are complete.

## Resume Rules

On resume:

1. Read `.deep-planning/state.md`.
2. Read the artifact for the current phase.
3. Verify whether the recorded status still matches the files.
4. Continue from the earliest incomplete or failed phase.
