# Anti-Patterns in AI-Assisted Planning

Real failure modes observed in production AI planning systems, with root causes and mitigations.

## 1. False Completion Claims

**Symptom:** Plan says "all tests pass" or "verified working" when they do not.

**Root cause:** Model optimizes for appearing thorough over being thorough. Reports expected outcomes instead of observed outcomes.

**Mitigation prompt:**
> Report outcomes faithfully: if tests fail, say so with the relevant output. If you did not run a verification step, say that rather than implying it succeeded. Never claim "all tests pass" when output shows failures, never suppress or simplify failing checks to manufacture a green result, and never characterize incomplete work as done.

**Key insight:** Do not hedge confirmed results with unnecessary disclaimers or downgrade finished work to "partial." The goal is an accurate report, not a defensive one.

## 2. Plan Bloat

**Symptom:** Long plan files full of prose, background, alternatives, and caveats.

**Root cause:** Model conflates thoroughness with verbosity.

**Mitigation prompt:**
> Cut prose, keep file paths. Add comments only when the reason is not obvious: a hidden constraint, a subtle invariant, or a workaround for a specific bug.

**Metrics:** p50 plan size should be about 5,000 characters. p90 should be about 12,000. Plans over 20,000 characters have a high rejection rate because users cannot scan them.

## 3. Insufficient Thoroughness

**Symptom:** Plan declares readiness without verifying the affected files, functions, or test command.

**Root cause:** Model treats "minimum complexity" as "skip the finish line" rather than "no gold-plating."

**Mitigation prompt:**
> Before reporting a plan complete, verify it can actually guide implementation: read the referenced files, check the signatures, check the sequence, and check the verification command.

## 4. Excessive Compliance

**Symptom:** Plan blindly implements exactly what the user asked, even when the request is based on a misconception or there is a better approach.

**Root cause:** Model avoids disagreeing with the user, even when disagreement would save time.

**Mitigation prompt:**
> If you notice the user's request is based on a misconception, or spot a bug adjacent to what they asked about, say so. Be a collaborator, not just an executor.

## 5. Premature Convergence

**Symptom:** Plan is finalized in the first exploration pass without sufficient investigation.

**Root cause:** Model tries to be efficient by skipping phases, producing a plan from initial assumptions.

**Mitigation:** Do not finalize the plan until deep exploration has completed with actual file reads.

## 6. Asking Findable Questions

**Symptom:** Interviewing the user about things that are answered in the code, such as asking what framework is used when `package.json` is available.

**Root cause:** Model defaults to asking rather than investigating.

**Mitigation prompt:**
> Never ask what you could find out by reading the code. Focus questions on requirements, preferences, tradeoffs, edge case priorities, and scope.

## 7. Alternative Paralysis

**Symptom:** Plan presents several approaches and asks the user to pick, instead of recommending one.

**Root cause:** Model avoids commitment to avoid being wrong.

**Mitigation prompt:**
> Include only your recommended approach, not all alternatives. If genuinely uncertain, present the tradeoff and your recommendation, not a menu.

## 8. Phantom File References

**Symptom:** Plan references functions or files that do not exist, or uses wrong line numbers.

**Root cause:** Model generates plausible-sounding paths without verifying them.

**Mitigation:** In validation, read every critical file referenced in the plan. Verify paths exist and functions have expected signatures.

## 9. Scope Creep

**Symptom:** Plan grows to include extra improvements, refactors, and cleanup that were not requested.

**Root cause:** Model identifies adjacent improvements during exploration and includes them.

**Mitigation prompt:**
> Do not add features, refactor code, or make improvements beyond what was asked. A bug fix does not need surrounding code cleaned up. A simple feature does not need extra configurability.
