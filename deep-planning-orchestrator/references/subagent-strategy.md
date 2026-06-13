# Subagent Strategy

Subagents are optional acceleration, not a dependency.

## Authorization

Use subagents only when explicitly allowed by the user or current session instructions. If not allowed, perform the same work locally.

## Good Subagent Uses

- independent repo exploration questions;
- independent review lenses;
- independent validation of a finished plan;
- execution tasks with disjoint write ownership.

## Bad Subagent Uses

- tasks that require immediate blocking decisions;
- overlapping write sets;
- vague "review everything" prompts;
- replacing required user decisions;
- delegating work that depends on hidden conversation context.

## Prompt Contract

Each subagent prompt must include:

- objective;
- relevant artifact paths;
- allowed write scope;
- forbidden actions;
- expected output format;
- whether it may ask questions.

## Fallback

If subagents are unavailable, run bounded local passes and record `Subagent fallback: local` in `state.md`.
