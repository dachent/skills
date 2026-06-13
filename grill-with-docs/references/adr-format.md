# ADR Format

ADRs live in `docs/adr/` and use sequential numbering: `0001-slug.md`, `0002-slug.md`, and so on.

Create the `docs/adr/` directory lazily, only when the first ADR is needed.

## Template

```md
# {Short title of the decision}

{1-3 sentences: what is the context, what did we decide, and why.}
```

That is enough for most ADRs. The value is recording that a decision was made and why, not filling out sections.

## Optional Sections

Only include these when they add genuine value:

- **Status** frontmatter: `proposed`, `accepted`, `deprecated`, or `superseded by ADR-NNNN`.
- **Considered Options**: include rejected alternatives only when they are worth remembering.
- **Consequences**: include non-obvious downstream effects.

## Numbering

Scan `docs/adr/` for the highest existing number and increment by one.

## When To Offer An ADR

All three must be true:

1. The decision is hard to reverse.
2. A future reader will wonder why it was done this way.
3. The decision involved a real tradeoff.

If a decision is easy to reverse, skip it. If it is not surprising, skip it. If there was no real alternative, skip it.

## What Qualifies

- Architectural shape.
- Integration patterns between contexts.
- Technology choices that carry lock-in.
- Boundary and ownership decisions.
- Deliberate deviations from the obvious path.
- Constraints not visible in the code.
- Rejected alternatives when the rejection is non-obvious.
