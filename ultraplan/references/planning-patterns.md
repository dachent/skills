# Planning Patterns Reference

## Plan File Variants

Different levels of plan detail for different task complexities.

### Minimal Plan (Simple Tasks)

```markdown
# Plan: [Title]

## Changes
- `path/to/file.ts:42` - [what changes]
- `path/to/file2.ts:15` - [what changes]

## Verify
`npm test -- --filter=relevant-test`
```

### Standard Plan (Medium Tasks)

```markdown
# Plan: [Title]

## Context
[One line: what and why]

## Changes

### [Module 1]
- **File**: `path/to/file.ts`
- **Change**: [description]
- **Reuses**: `existingFn()` from `utils.ts:42`

### [Module 2]
- **File**: `path/to/file2.ts`
- **Change**: [description]

## Sequence
1. [First - least dependent change]
2. [Second - builds on first]
3. [Third - integration]

## Verify
`npm test && npm run lint`
```

### Detailed Plan (Complex/Architectural Tasks)

```markdown
# Plan: [Title]

## Context
[One paragraph: problem, trigger, intended outcome]

## Architecture Decision
[Which approach and why - one paragraph max]

## Changes

### [Component 1]
- **File**: `path/to/file.ts:42`
- **Change**: [specific change]
- **Reuses**: `existingFn()` from `utils.ts:42`
- **New**: `newFunction(param: Type): ReturnType` - [why needed]

### [Component 2]
- **File**: `path/to/file2.ts:15`
- **Change**: [specific change]
- **Depends on**: Component 1

### [Tests]
- **File**: `path/to/file.test.ts`
- **Add**: [test cases covering the change]

## Sequence
1. [First step] - `file.ts` - [what and why this order]
2. [Second step] - `file2.ts` - [dependency reason]
3. [Third step] - `file.test.ts` - [verify before integration]
4. [Fourth step] - integration verification

## Edge Cases
- [Edge case 1]: [how the plan handles it]
- [Edge case 2]: [how the plan handles it]

## Risks
- [Risk 1]: [mitigation]
- [Risk 2]: [mitigation]

## Verify
```bash
# Unit tests
npm test -- --filter=relevant

# Integration check
npm run build && npm run e2e

# Manual smoke test
[specific steps]
```
```

## Multi-Agent Exploration Strategies

Use these only when Codex subagents are available and the user explicitly asked for subagents or parallel agent work.

### Pattern: Breadth-First Discovery

Launch 3 agents, each scanning a different layer:
- Agent 1: Data layer (models, schemas, database)
- Agent 2: Business logic (services, utilities, core)
- Agent 3: Presentation layer (components, routes, API endpoints)

### Pattern: Feature Trace

Launch 2 agents following a feature through the stack:
- Agent 1: Trace from UI to API to service to database
- Agent 2: Find all related tests and similar features

### Pattern: Impact Analysis

Launch 2 agents assessing blast radius:
- Agent 1: What directly changes
- Agent 2: What indirectly depends on the changed code (imports, callers, consumers)

## Interview Question Templates

### Requirements Clarification

- "I see [existing pattern]. Should this change follow the same approach, or is there a reason to diverge?"
- "This touches [N] files. Should I scope this to [subset] first, or go all-in?"
- "[Feature X] and [Feature Y] could conflict. Which takes priority?"

### Architecture Decisions

- "I found two approaches: [A] is simpler but [tradeoff], [B] is more complex but [benefit]. Given your priorities, I recommend [A/B]. Should I plan around that?"
- "The existing code uses [pattern]. This task could extend it or replace it. I recommend [choice] because [reason]. Should I proceed with that assumption?"

### Scope Management

- "While exploring I found [adjacent issue]. Should I include it in this plan or track it separately?"
- "The minimum viable change is [X]. The complete change also needs [Y, Z]. Where should I draw the line?"
