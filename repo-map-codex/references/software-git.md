# Software With Git Map

Capture:

- branch, status, recent commits, remotes if relevant;
- package managers and lockfiles;
- build, test, lint, typecheck, and smoke commands;
- entrypoints and routes;
- important modules and ownership boundaries;
- migrations, schemas, generated code, fixtures, and test data;
- CI configuration and required checks;
- risky shared files;
- similar working implementations.

Do not run mutating commands. Read-only Git commands and tests/builds that do not intentionally edit tracked source are allowed when they improve the map.
