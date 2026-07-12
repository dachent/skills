# Sources and provenance

## Purpose

Separate source lineage, factual claims, local adaptations, and new architecture.

Do not use this document as a substitute for repository license files or legal review.

## Original scaffold

- Source: `https://gist.github.com/dachent/cdc05151d047708c290bd4da0aaeed96`
- File: `claude_code_deep_planning.txt`
- Displayed raw revision during preparation: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Existing repository provenance snapshot revision: `0aadb9e28397b07a75853d40a78610bc21cebc81`
- Ownership: the gist and this repository have the same owner
- Distribution: governed by the repository policy; no separate third-party permission is required for inclusion

The raw rendered content is preserved in `original/claude_code_deep_planning.txt`. Byte-level hidden Unicode equivalence remains to be verified. This is a fidelity check, not an ownership or permission blocker.

## Existing repository planning ports

Repository: `dachent/skills`

Relevant packages:

- `deep-planning-codex`;
- `repo-map-codex`;
- `verification-plan-codex`;
- `adversarial-plan-review-codex`;
- `ultraplan-codex`;
- `grill-me-codex`;
- `grill-with-docs-codex`;
- `handoff-codex`.

These provide current implementation evidence and should not be confused with the new generalized runtime architecture.

## Matt Pocock skills

- Repository: `mattpocock/skills`
- Reviewed revision in repository provenance: `391a2701dd948f94f56a39f7533f8eea9a859c87`
- License: MIT
- Relevant concepts: grilling, document-grounded grilling, handoff, separation of user-invoked orchestrators and model-invoked disciplines.

## UltraPlan

- Repository: `6missedcalls/ultraplan`
- Reviewed revision in repository provenance: `06779940475f9c52b4d3b546d309b2c31ebbf8ea`
- License: MIT
- Role: Claude-oriented deep repository planning; source for the heavy Codex adaptation `ultraplan-codex`.

## Superpowers

- Repository: `obra/superpowers`
- License observed: MIT
- Role: brainstorming, systematic debugging, planning, execution, parallel/subagent development, review, and verification disciplines.
- Provenance action required: add an immutable reviewed revision to the repository source registry before treating it as a locked runtime dependency.

## Zenith

- Repository: `Intelligent-Internet/zenith`
- Reviewed revision during preparation: `feb1d62264b927cdf9a0d6ed3d14037a8cba0e60`
- Code license: Apache-2.0
- Technical report and figures: CC BY 4.0, according to the repository README
- Role in this package: comparative architecture and future optional execution backend, not copied implementation.

Zenith claims and benchmark figures in `04-zenith-comparison.md` are attributed to its maintainers and should be rechecked when the source revision changes.

## New repository-owned material

The following are new architecture/synthesis rather than copied upstream skill instructions:

- generalized project-state and delivery model;
- transactional `projectctl` architecture;
- SQLite plus event-log state design;
- provider result and state-mutation boundary;
- trust and approval model;
- corrected QC and smoke-test split;
- staged shadow-mode migration;
- comparative synthesis of the scaffold and Zenith;
- adversarial review conclusions.

## Required release checks

Before a release:

1. verify the raw gist byte-for-byte, including hidden Unicode;
2. record that the gist and repository share the same owner;
3. register Superpowers with an immutable revision and license evidence before treating it as a locked runtime dependency;
4. retain MIT notices for adapted Matt Pocock and UltraPlan material where applicable;
5. retain Zenith attribution for report-derived claims;
6. distinguish repository-owned architecture from attributed third-party material;
7. run repository provenance validation.

## License clarification

Ownership and licensing are separate questions. Common ownership of the gist and repository removes the prior permission uncertainty. It does not automatically create an open-source license. In the absence of a root or package-specific license grant, repository-owned material remains all rights reserved and distribution is governed by repository policy.
