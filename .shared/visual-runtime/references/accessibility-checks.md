# Accessibility checks

Use these checks with screenshots and visual lint output. They are a floor, not a full accessibility audit.

## Mechanical Checks

- Text contrast meets WCAG AA where practical.
- Font sizes are readable at the target viewport.
- Interactive controls have visible labels or accessible names.
- Focus order and keyboard interaction remain predictable.
- Tap targets are not cramped on mobile.
- Images that communicate meaning have text alternatives in the source artifact.

## Visual Checks

- Color is not the only way to distinguish state.
- Important content remains readable under mobile wrapping.
- Charts include labels, units, legends, or direct annotations.
- Motion or animation does not hide essential information.

## Evidence

Preserve the visual-lint JSON and screenshots that support the review. If an issue is accepted, record why it is acceptable for the audience and artifact.

## Boundary

The shared visual runtime can flag obvious issues, but it does not replace a full accessibility review. Future skills can add stricter audits on top of this baseline.
