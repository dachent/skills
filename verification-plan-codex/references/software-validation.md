# Software Validation

For each success criterion, prefer the strongest available proof:

1. targeted automated test;
2. integration or end-to-end test;
3. typecheck/build/lint/static analysis;
4. smoke command or CLI run;
5. manual UI/API check with exact steps and expected result.

Record exact commands, working directory, expected output, and what failure looks like.

Do not accept "run tests" without naming the command and relevant test scope.
