# Software Review Lens

Check:

- referenced paths, functions, commands, and tests exist;
- implementation order is dependency-safe;
- migrations, schemas, generated files, and config changes are accounted for;
- validation commands exercise the changed behavior;
- rollback is defined;
- security, privacy, auth, data loss, and compatibility risks are considered;
- subagent work packages have disjoint ownership.

Block execution if any critical path is unverified.
