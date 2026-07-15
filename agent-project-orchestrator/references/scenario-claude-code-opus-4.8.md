# Scenario: Claude Code with Opus 4.8

## Operating contract

Use explicit scope, applicability, coverage, provider triggers, and phase boundaries. Preselect the methodology capability sequence before work begins. Do not rely on the orchestrator to generalize a rule beyond the scope stated in the contract.

## Control policy

- Continue within one approved phase at a time.
- Stop at project-contract, material post-investigation, design-selection, execution-plan, scope-change, and destructive/external-action gates.
- Update durable state after every major phase.
- Use comprehensive intermediate artifacts when they reduce ambiguity or improve resumption.
- Permit at most one autonomous repair attempt before surfacing a blocker.
- Limit parallel workers to two and delegate only independent, clearly bounded work.

## Routing behavior

The deterministic router selects capabilities and their order. Opus executes the selected route and may recommend a route change, but it must record and obtain approval for a material methodology change rather than silently restructuring the project.

## Verification

Require a fresh-context terminal review at independence level 3 or higher. Completion remains blocked until current outputs and evidence satisfy the original project contract.
