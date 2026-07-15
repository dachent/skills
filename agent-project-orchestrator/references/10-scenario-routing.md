# Scenario routing MVP

## Decision

Support exactly three certified harness/model scenarios in the first implementation:

1. `claude-code-opus-4.8`
2. `claude-code-sonnet-5`
3. `codex-gpt-5.6-sol`

Do not generalize into independent harness and model inheritance layers yet. Resolve an exact scenario first, then apply its orchestration policy over the shared project methodology.

## Resolution order

```text
project request
    -> shared project classifier
    -> shared methodology capability route
    -> exact harness/model scenario resolution
    -> scenario orchestration overlay
    -> harness-compatible provider resolution
    -> invariant and risk clamps
    -> execution or hard stop
```

The shared project router decides which capabilities are materially required. The scenario overlay controls how those capabilities are sequenced, gated, delegated, budgeted, and recorded.

## Shared methodology versus scenario policy

Keep these shared:

- project-state and delivery-mode classification;
- success and failure contracts;
- logical capability selection;
- evidence and traceability requirements;
- approval provenance;
- destructive-action controls;
- terminal-verification requirements.

Make these scenario-specific:

- instruction style;
- capability-selection discretion;
- gate density;
- continuation mode;
- state-update frequency;
- provider-loading behavior;
- repair and parallelism budgets;
- intermediate artifact detail;
- preferred terminal-review mode.

## Precedence

Apply policy in this order:

1. non-overridable policy floor;
2. project risk and correctness requirements;
3. provider contract constraints;
4. exact scenario profile;
5. efficiency preferences.

A scenario may add controls but may not weaken the policy floor.

## Unsupported pairs

Hard-stop on a harness/model pair that does not resolve to one of the three scenario IDs. Do not infer a nearby scenario from model family, provider, or naming similarity.

## Provider handling

Use the scenario harness when resolving providers. A provider installed for another harness does not satisfy capability preflight. Do not silently perform a required capability locally when no compatible provider exists.

## Initial status

These profiles are explicit starting policies, not universal claims about model behavior. Certify and revise them using common fixtures that measure unnecessary phases, approval interruptions, provider-selection accuracy, state consistency, resume behavior, validation quality, and false-completion rate.
