# WKFINOPS-807 worker heartbeat + caps

## Intent
Stop a long native Excel preflight from being mistaken for a dead job, while retaining a deterministic upper bound. The original operational failure was three repeated one-hour attempts; the repository correction already preserves branded native timeouts and prevents those retries.

## Current mechanism
The supervisor tails worker `events.jsonl`; any worker event refreshes inactivity, while whole-job and phase deadlines remain independent. Its one-Hz telemetry samples are supervisor-generated and therefore do not prove worker progress. Existing worker heartbeats cover only a post-refresh polling loop, not synchronous composite-preflight COM calls.

## Chosen approach
Add a worker-originated heartbeat every five seconds during composite preflight, using the existing `WorkerEvent` schema and current phase with a distinguishing heartbeat message. A timer is required because synchronous COM calls prevent the STA work loop from emitting. Make `EventWriter` safe for the worker and timer threads, and stop/dispose the heartbeat on every exit path.

Retain the existing inactivity watchdog and absolute whole-job/phase caps. A heartbeat may defer an inactivity kill; it never extends an absolute cap. Heartbeat means the worker is alive, not that a particular row completed.

## Alternatives and tradeoffs
- Supervisor-only heartbeat: rejected; it stays alive when the worker is hung.
- Existing refresh-loop heartbeat only: rejected for this incident; it cannot fire during synchronous preflight.
- Full row/deadline telemetry: separated by the owner into WKFINOPS-833. This increment adds no `rows_done`, deadline-ratio, or >80% warning.

## Constraints
No schema change, patient data, production run, or global runtime overwrite. Work stays on session branch `WKFINOPS-807-native-heartbeat`; runtime promotion remains a separate controlled step.

## Acceptance
- Deterministic native tests prove heartbeat emission during a deliberately blocked preflight, thread-safe event writes, and disposal without later writes.
- Supervisor tests prove same-phase heartbeat refreshes inactivity without moving the absolute whole-job/phase deadlines.
- Native unit suite and build pass; an opt-in integration test proves a hung worker is still killed by the absolute cap.
- The weekly-run observation on fresh `-08` records heartbeat events and either completion or one named timeout, never three retries.

## Builder discretion
Choose the smallest timer/locking implementation consistent with existing C# idioms. Keep heartbeat failure behavior explicit and avoid changing unrelated runtime behavior.
