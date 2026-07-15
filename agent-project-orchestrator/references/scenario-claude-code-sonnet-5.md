# Scenario: Claude Code with Sonnet 5

## Operating contract

Provide clear goals, constraints, success criteria, and a bounded process. Use the shared router to select the required capability set, but allow Sonnet to skip an optional selected capability when current evidence makes it unnecessary and the skip is recorded with rationale.

## Control policy

- Continue through approved task batches or a bounded sprint.
- Stop at project-contract, material architecture, execution-sprint, scope-change, and destructive/external-action gates.
- Update durable state after each task batch.
- Use moderate intermediate artifact detail.
- Permit up to two bounded repair attempts.
- Limit parallel workers to three and reconcile results through one authoritative state writer.

## Routing behavior

The router defines the allowed capability graph. Sonnet may optimize sequence and omit non-material optional work, but it may not add material scope, weaken validation, or bypass a reserved human decision.

## Verification

Require a fresh-context terminal review at independence level 3 or higher. Record skipped capabilities and verify that each acceptance criterion still has current evidence.
