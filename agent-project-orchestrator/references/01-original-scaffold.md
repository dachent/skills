# Original Claude Code scaffold

## Purpose of this record

This package preserves the original scaffold as historical source material before describing later generalization or architectural changes.

The raw transcription is stored at:

- [`original/claude_code_deep_planning.txt`](original/claude_code_deep_planning.txt)

## Source identification

- Gist owner: `dachent`
- Gist ID: `cdc05151d047708c290bd4da0aaeed96`
- File shown by GitHub: `claude_code_deep_planning.txt`
- Gist description: `Deep planning general prompt template`
- Displayed raw revision: `6ea4c02e5aa60c9991e1e4d1c50089c01cd6ec83`
- Gist page last-active date observed during package preparation: June 13, 2026

## Preservation rule

Do not edit the raw file to make it platform-neutral or to reflect later design decisions. It exists to preserve the starting point.

Corrections, interpretation, generalization, and critique belong in later reference files.

## Byte-level caveat

GitHub warns that the source contains hidden or bidirectional Unicode text. The file in this package is a verbatim transcription of the content rendered by GitHub at the identified revision. The preparation environment could not independently download and byte-compare the raw gist, so hidden Unicode equivalence has not been certified.

Before release outside the repository, retrieve the raw revision, compare byte-for-byte, and replace this transcription if any hidden characters differ.

## What the original scaffold does

The scaffold creates a sequential, gated flow:

1. sharpen criteria and scope;
2. catalog the complete evidence set;
3. inspect and classify materials;
4. perform a failure autopsy and create a Dead Ends Registry;
5. attack assumptions against the actual failure corpus;
6. run targeted probes;
7. brainstorm a design constrained by known dead ends;
8. create a grounded UltraPlan;
9. convert it into a final execution plan with validation and rollback;
10. initialize state and dependencies;
11. execute through subagents, parallel agents, or plan batches;
12. verify against the initial success criteria and archive the handoff.

Its most consequential design choices are:

- explicit user proceed gates;
- repeated durable handoffs;
- failure-corpus grounding;
- a persistent Dead Ends Registry;
- clear separation of exploration, planning, execution, and verification;
- deliberate refusal to improvise around blocking failures.

Those properties are retained in the generalized design, but made adaptive rather than universally linear.
