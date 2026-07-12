# GitHub Actions orchestration

`skills-manifest.json` determines which supported skills require hosted validation. `tools/ci_matrix.py` generates an affected-skill matrix for pull requests and ordinary pushes, or a complete matrix for scheduled and explicitly requested runs.

## Change expansion

A change beneath a canonical skill directory selects that skill. A change beneath a declared shared component selects every manifest consumer. Changes to the manifest, CI planner, result runner, or primary validation workflow select every supported skill. Archived skills are excluded.

`cross-platform` expands to `ubuntu-latest`, `windows-latest`, and `macos-latest`. Explicit `linux`, `windows`, and `macos` claims map only to their corresponding approved GitHub-hosted runner. Unknown platform claims fail planning instead of being silently omitted.

## Workflow conventions

Repository workflows must:

- declare least-privilege `permissions`;
- define job timeouts and workflow concurrency where repeated runs can overlap;
- use approved GitHub-hosted runners or the separately protected Office runner labels;
- disable persisted checkout credentials;
- pin every external action to an immutable 40-character commit SHA;
- allow Dependabot to propose action-pin updates;
- preserve the stable `Validate / Required` aggregation check.

`tools/validate_actions.py` enforces these controls.

## Test authorities

The generic matrix performs structural validation for every selected skill and executes the manifest's hosted commands unless the skill delegates domain semantics to a specialized workflow. `.github/workflows/code-mapper-codeql.yml` remains authoritative for Code Mapper lifecycle, benchmark, and live CodeQL tests. `.github/workflows/office-smoke.yml` remains the protected Office runtime harness. The validation workflow only schedules or aggregates those authorities.

Each skill job writes a schema-versioned JSON result under `.test-results/` and uploads it as `skill-result-<skill>-<runner>`. Specialized workflows use the same envelope while retaining their detailed diagnostics.

## Scheduled validation and repository health

`Validate` runs the full hosted matrix weekly. `Repository Health` runs monthly and aggregates the existing manifest, generated-artifact, provenance, and action-policy validators. It also reports skills without hosted tests, stale reviews, missing source-registry coverage, unpinned actions, and mirror drift. The workflow updates a persistent repository-health issue when attention is required.

## Branch protection

Protect `main` with the stable check name **Validate / Required**. Specialized job names may evolve without changing the branch-protection contract because the `Required` job accepts only successful or intentionally skipped dependencies.
