# RFC 0001: xlsx-win reliable Excel runtime v2

- Status: Proposed
- Date: 2026-07-11
- Scope: `xlsx-win` and shared Windows Office runtime
- Decision owner: repository maintainer

## Executive decision

Keep one user-facing `xlsx-win` skill with one versioned job contract and one Python-facing control plane.

The runtime will use:

1. a Python control plane for workbook classification, file-backend selection, staging, manifests, validation, and result interpretation;
2. a C# Windows supervisor for interactive-session execution, process ownership, timeouts, retries, telemetry, modal-dialog detection, and worker recovery;
3. two execution adapters during migration:
   - Path A: hardened out-of-process Excel COM;
   - Path C: an in-process C# Excel controller, which becomes the production default;
4. Path A retained after migration only for diagnostics, recovery, compatibility, and constrained fallback;
5. deterministic selection among Python and .NET workbook file engines before Excel compute;
6. desktop Excel as the authoritative engine for refresh, calculation, Power Query, Data Model, pivots, links, approved macros, and saved cached values.

Path C does not replace Path A's supervision, validation, staging, and recovery infrastructure. It replaces Path A's high-volume direct COM driving.

## Problem

The current implementation launches PowerShell scripts that create hidden Excel COM instances, call `RefreshAll`, wait for some asynchronous work, perform `CalculateFullRebuild`, save, and emit limited JSON.

This provides broad native Excel coverage, but it is not a reliable job system. A nominal timeout does not bound Excel startup, workbook open, refresh, async waits, save, close, or quit. Modal prompts can block indefinitely. A returned COM call is not proof that all data refreshed successfully. Repeated Excel launches add latency and state risk. The current validation detects visible cached formula errors but cannot prove data freshness or semantic correctness.

## Goals

- Give an LLM agent one stable, typed, machine-readable Excel interface.
- Convert indefinite hangs into bounded, attributable failures.
- Distinguish refresh, calculation, validation, save, and publication states.
- Preserve native Excel fidelity.
- Reduce repeated Excel launches and cross-process COM calls.
- Support workbook-specific correctness contracts.
- Route file creation and editing to the fastest safe engine.
- Keep the worker implementation Windows/Excel-specific while allowing the agent and queue to run anywhere.
- Make failures reproducible through logs, event streams, screenshots, process metadata, and immutable inputs.

## Non-goals

- Running full-fidelity Excel compute on Linux or in a headless container.
- Treating Excel Desktop as a horizontally concurrent server within one Windows session.
- Proving that arbitrary third-party add-ins are safe or automatable.
- Reimplementing Power Query, the Excel calculation engine, VBA, or the Data Model.
- Promising that every workbook will refresh successfully.
- Making the LLM choose implementations through subjective workbook-complexity judgments.

## Upstream status

The repository pins `anthropics/skills` at commit `57546260929473d4e0d1c1bb75297be2fdfa1949` from 2026-06-15. At review time, upstream `main` is two commits ahead, and both commits modify only `skills/claude-api`. There are no upstream `skills/xlsx` changes to incorporate.

The baseline Anthropic skill remains useful for general spreadsheet behavior, formula discipline, template preservation, and output conventions. Its LibreOffice recalculation path is intentionally not authoritative for `xlsx-win`, because it does not provide desktop Excel fidelity for Power Query, workbook connections, Data Model behavior, pivots, add-ins, VBA, and Excel-specific cached values.

## Why no complete existing product solves this

The market has partial solutions, not the combined system required here:

- file libraries create or edit OOXML but do not execute the complete Excel runtime;
- Microsoft Graph and Office Scripts expose only subsets of workbook behavior;
- RPA products automate the UI but inherit desktop state, prompts, and weak semantic validation;
- COM wrappers such as pywin32, xlwings, and similar tools expose Excel but do not supply a complete supervised job protocol, process fencing, workbook contracts, recovery, and LLM-safe result semantics;
- add-in frameworks such as Excel-DNA provide an in-process extension mechanism, not an end-to-end agent execution service;
- commercial spreadsheet engines can calculate and manipulate many workbook features but cannot guarantee native behavior for every Power Query connector, VBA project, COM add-in, XLL, RTD feed, Data Model operation, and Excel-version-specific behavior;
- Microsoft does not support Office Desktop as a general unattended server product.

A reliable agent runtime therefore has to combine several layers that vendors normally sell separately: file manipulation, desktop-session orchestration, add-in execution, process supervision, semantic validation, observability, policy, and recovery. The addressable market is also fragmented by workbook-specific dependencies, Office licensing, connector credentials, add-ins, bitness, user profiles, and security policy. This makes a universal turnkey product difficult to support economically.

## Architecture

```text
LLM / caller
    |
    v
xlsx-win skill
    |
    v
Python control plane
    |-- classify workbook and requested operation
    |-- choose file backend
    |-- stage immutable input and working copy
    |-- create versioned job manifest
    |-- submit job and interpret result
    |
    v
C# Windows supervisor
    |-- durable job state and heartbeat
    |-- one active job per worker/session
    |-- Excel PID and Windows Job Object ownership
    |-- phase deadlines and cancellation
    |-- COM message filter and retry policy
    |-- UI Automation modal detection
    |-- screenshots and window inventory on failure
    |-- graceful shutdown, forced termination, retry, VM recycle
    |
    +--> Path A adapter: hardened out-of-process COM
    |
    +--> Path C adapter: in-process Excel controller
              |-- named-pipe or equivalent local IPC
              |-- Excel main-thread execution
              |-- per-object refresh and state reporting
              |-- bulk range writes
              |-- approved macro entrypoints
              |-- structured progress events
```

## One skill, not two

There will be one `xlsx-win` skill. Separate Path A and Path C skills would duplicate routing, validation, error semantics, documentation, and tests. Backend choice is an implementation detail represented in the job manifest and final result.

The agent-facing commands should remain stable:

- `inspect`
- `create`
- `edit`
- `refresh`
- `calculate`
- `refresh-and-calculate`
- `run-approved-macro`
- `validate`
- `diagnose`

## Versioned job contract

The contract must be JSON Schema-backed and reject unknown or unsafe fields by default.

Example:

```json
{
  "schema_version": "1.0",
  "operation": "refresh_and_calculate",
  "input_workbook": "C:\\jobs\\input\\model.xlsm",
  "output_workbook": "C:\\jobs\\output\\model.refreshed.xlsm",
  "backend": "auto",
  "file_backend": "auto",
  "refresh_profile": "full",
  "calculation": "full_rebuild",
  "macro_policy": "disabled",
  "approved_macro": null,
  "update_external_links": false,
  "timeouts": {
    "start_excel_seconds": 30,
    "open_workbook_seconds": 90,
    "refresh_total_seconds": 1800,
    "calculation_seconds": 900,
    "save_seconds": 90,
    "close_seconds": 30
  },
  "validation_contract": "C:\\jobs\\contracts\\model.contract.json",
  "idempotency_key": "sha256:..."
}
```

Result schema:

```json
{
  "schema_version": "1.0",
  "run_id": "01J...",
  "status": "succeeded",
  "backend": "addin",
  "phase": "completed",
  "refresh_completed": true,
  "calculation_completed": true,
  "validation_passed": true,
  "published": true,
  "duration_seconds": 87.4,
  "warnings": [],
  "artifacts": {
    "output_workbook": "...",
    "events_jsonl": "...",
    "run_json": "...",
    "validation_json": "...",
    "log": "...",
    "screenshots": []
  }
}
```

## File-backend routing

File manipulation and Excel compute are separate decisions.

| Workload | Preferred backend | Notes |
| --- | --- | --- |
| New formatted workbook | XlsxWriter | Default open-source creation engine |
| New dense rectangular workbook | PyExcelerate | Optional fast path after benchmark and feature checks |
| Data analysis and reshaping | pandas or Polars | Not the fidelity layer |
| Fast XLSX reads | fastexcel/calamine where compatible | Avoid openpyxl object creation when only values are needed |
| Ordinary existing workbook edits | openpyxl | Compatibility backend, not universal default |
| Narrow edits to large templates | targeted OOXML patcher | Explicit supported operations only |
| Strongly typed .NET package editing | Open XML SDK | Preferred for controlled OOXML operations in worker |
| Complex existing workbook editing | optional Aspose.Cells | Commercial, benchmark and fidelity gate required |
| Native objects or workbook already opened for compute | Path C bulk writes | Avoid a second XLSX serialization |
| Refresh, Power Query, Data Model, pivots, links, native calculation | Excel Path C | Authoritative runtime |

The automatic router must be deterministic. It should use requested operations, file type, workbook feature inventory, edit shape, estimated cell volume, and fidelity requirements. It must not rely on an LLM's subjective judgment that a workbook is "simple."

## Path A: hardened COM adapter

Path A is required first because it establishes the common reliability shell and provides a fallback while Path C is built.

Required capabilities:

- Python-facing CLI and JSON Schema contract;
- isolated child process per Excel job;
- explicit STA initialization and message pumping;
- `IMessageFilter` retry handling for rejected COM calls;
- Excel PID capture and Windows Job Object ownership;
- global session mutex and per-workbook distributed lock;
- immutable input and local SSD working copy;
- phase-specific deadlines enforced outside Excel;
- heartbeat and append-only event stream;
- UI Automation detection of modal dialogs;
- screenshot and window inventory on failure;
- graceful close, forced process-tree termination, and one clean retry;
- explicit per-connection, query-table, model, pivot, and calculation state inspection where the object model permits it;
- save to a new output, close, reopen read-only, and revalidate;
- no publication unless the validation contract passes.

Path A must stop launching Excel multiple times for one Power Query operation. Modify, refresh, calculate, verify, and save should occur within one owned Excel lifecycle whenever possible.

## Path C: in-process Excel controller

Path C becomes the normal production backend.

Recommended implementation:

- C# add-in using Excel-DNA unless a proof of concept demonstrates a material reason to use VSTO or native C++;
- signed and versioned deployment artifact;
- local named-pipe protocol authenticated to the owning supervisor process and Windows user;
- all Excel object-model work marshalled to Excel's main thread;
- one job accepted at a time;
- structured state events and heartbeats;
- bulk rectangular range writes rather than cell-by-cell calls;
- explicit connection/query/model/pivot refresh sequencing;
- optional approved macro execution by exact allowlisted name;
- cancellation checkpoints between phases;
- no network listener and no arbitrary code execution API;
- add-in health/version handshake before every job.

The supervisor still owns process lifecycle, deadlines, modal detection, staging, validation, retry, and machine recovery.

## Workbook validation contracts

Generic formula-error scanning is necessary but insufficient. Important workbooks require sidecar contracts.

Contracts can assert:

- required sheets, tables, names, queries, connections, model tables, pivots, and links;
- expected row-count and column-count ranges;
- source and workbook as-of timestamps;
- maximum allowed data age;
- sentinel cells and formula results;
- expected calculation mode;
- prohibited visible and hidden error values;
- absence of unexpected circular references;
- approved macro entrypoint and expected postcondition;
- output hash, workbook-open verification, and publication policy.

A successful COM call is never sufficient evidence of success.

## State machine

Every job records transitions:

```text
QUEUED
STAGING_INPUT
INSPECTING_WORKBOOK
SELECTING_BACKENDS
STARTING_EXCEL
OPENING_WORKBOOK
APPLYING_EDITS
UPDATING_LINKS
REFRESHING_CONNECTIONS
REFRESHING_DATA_MODEL
REFRESHING_PIVOTS
CALCULATING
RUNNING_APPROVED_MACRO
VALIDATING
SAVING
REOPEN_VALIDATION
PUBLISHING
SUCCEEDED | FAILED | TIMED_OUT | CANCELLED
```

Every event records run ID, timestamp, phase, Excel PID, Excel version, workbook hash, elapsed time, memory, retry number, current object where available, and normalized error information.

## Adversarial review

### Failure: the add-in itself destabilizes Excel

Mitigation:

- use managed C# rather than native C++ unless profiling proves otherwise;
- keep the add-in narrow;
- prohibit arbitrary plugin loading and arbitrary code execution;
- sign releases;
- pin dependencies;
- crash-test and soak-test representative workbooks;
- retain Path A diagnostics and a kill/recycle boundary outside Excel.

### Failure: named-pipe commands execute on the wrong Excel thread

Mitigation:

- never touch the Excel object model directly from the pipe listener thread;
- marshal all work to Excel's main thread through the add-in framework's supported mechanism;
- enforce serial execution;
- add thread-affinity assertions in debug and tests.

### Failure: Path A fallback masks a Path C defect

Mitigation:

- fallback only for enumerated failure classes such as add-in unavailable or version mismatch;
- do not fallback automatically after workbook logic, connector, credential, validation, or data-quality failures;
- record fallback reason and both backend attempts;
- provide a strict `backend=addin` mode for production certification.

### Failure: file-backend edits corrupt unsupported workbook parts

Mitigation:

- route macro-enabled, signed, external-link-heavy, Data Model, slicer, and complex drawing workbooks away from unsafe libraries;
- use copy-on-write staging;
- inventory OOXML parts before and after edits;
- validate package relationships;
- prefer targeted patching or native Excel for narrow complex edits;
- maintain a fidelity regression corpus.

### Failure: Excel reports success with stale data

Mitigation:

- inspect per-object state where available;
- require workbook-specific freshness sentinels;
- compare timestamps, row counts, and expected source markers;
- reopen and validate the saved output;
- make `success` impossible without contract completion.

### Failure: a hidden prompt blocks the worker

Mitigation:

- run Excel visibly on an isolated desktop session;
- monitor owned windows with UI Automation or WinEvent hooks;
- classify known dialogs;
- fail closed on unknown dialogs;
- capture screenshots and window text before termination.

### Failure: credentials or privacy settings are machine-specific

Mitigation:

- provision a dedicated user profile;
- preflight every required connector and driver;
- separate machine certification from workbook execution;
- never let the LLM enter credentials into arbitrary dialogs;
- record connector and driver inventory without secrets.

### Failure: malicious workbook code or data exfiltration

Mitigation:

- macros disabled by default;
- approved macros allowlisted by exact workbook hash, signature, and entrypoint;
- Protected View and trust-center policy explicitly managed;
- network egress constrained to approved sources;
- worker account least-privileged;
- output publication gated;
- untrusted workbooks run in a separate worker pool or are rejected.

### Failure: add-in packaging exceeds skill constraints

Mitigation:

- keep source and build instructions in this repository;
- publish signed binaries as GitHub Release artifacts or a separate runtime package;
- do not embed large binaries in the ChatGPT skill package;
- the skill detects and reports missing or incompatible runtime versions.

### Failure: one Windows session becomes a throughput bottleneck

Mitigation:

- one active Excel job per worker;
- horizontal scale through multiple isolated Windows workers;
- route file-only operations outside Excel;
- cache workbook feature inventories;
- reuse an Excel process only after soak testing proves isolation, otherwise use one process per job;
- use deterministic queueing and backpressure.

### Failure: C# adds build and deployment complexity

Mitigation:

- use the free .NET SDK and reproducible builds;
- publish self-contained or framework-dependent artifacts based on measured deployment needs;
- automate signing and release manifests;
- keep Python as the stable caller interface;
- provide a runtime self-test and version handshake.

## Security model

- The LLM cannot submit arbitrary VBA, C#, PowerShell, shell commands, file paths outside approved roots, or arbitrary COM method names.
- Job schema uses enumerated operations.
- Macros require explicit opt-in and allowlisting.
- Input and output roots are policy controlled.
- Network access is constrained by worker policy.
- Named-pipe access is local, user-bound, process-associated, and version-handshaked.
- Logs redact connection strings, tokens, user names where required, and workbook data samples by default.
- Every output is traceable to input hash, job manifest, runtime version, and validation contract.

## Testing strategy

### Hosted tests

- JSON Schema and result-schema validation;
- Python routing and manifest tests;
- OOXML package-diff and fidelity tests;
- C# build, unit tests, analyzers, and protocol tests;
- no Office COM required.

### Self-hosted Office tests

- simple formulas;
- Power Query worksheet load;
- Power Query Data Model load;
- pivots and pivot caches;
- external workbook links;
- approved macros;
- error formulas;
- slow and hanging connectors;
- expired credentials;
- locked files;
- modal dialogs;
- rejected COM calls;
- calculation timeout;
- failed save;
- disconnected or locked desktop;
- orphan process recovery;
- add-in missing, wrong version, and crash;
- repeated-run soak tests.

### Certification corpus

Maintain anonymized representative workbooks with explicit expected outputs and failure modes. A runtime release is not production-eligible until it passes the corpus and a sustained soak run.

## Metrics and targets

Initial targets to validate empirically:

- 100% of jobs terminate in a bounded final state;
- at least 95% of failures identify the failing phase and normalized cause;
- at least 90% reduction in orphan Excel processes;
- at least 80% reduction in transient COM-call failures under fault injection;
- zero publication after failed validation;
- at least 30% lower automation overhead for workflows that currently open Excel multiple times;
- no material regression in native workbook fidelity across the certification corpus.

These are release goals, not guaranteed estimates.

## Delivery plan

### Phase 0: contract and benchmarks

- define schemas, state machine, error taxonomy, artifact layout, security policy, and benchmark corpus;
- benchmark current runtime and file backends;
- add upstream-drift check confirming no missing Anthropic XLSX changes.

### Phase 1: Python control plane and file router

- implement stable CLI;
- feature inventory;
- deterministic backend router;
- XlsxWriter, PyExcelerate, openpyxl, pandas/Polars, fast reader, OOXML patcher, Open XML SDK, and optional Aspose capability adapters;
- immutable staging and package-diff validation.

### Phase 2: hardened Path A

- C# supervisor foundation;
- process ownership, STA worker, COM message filter, phase timeouts, locks, telemetry, modal detection, recovery;
- one Excel lifecycle per job;
- semantic validation and publication gate.

### Phase 3: Path C proof of concept

- Excel-DNA add-in;
- health/version handshake;
- named-pipe protocol;
- main-thread dispatcher;
- refresh, calculate, bulk write, inspect, and approved macro operations;
- fault injection.

### Phase 4: Path C productionization

- signing and release packaging;
- worker installer and upgrade/rollback;
- certification corpus and soak testing;
- Path C default routing;
- strict fallback policy.

### Phase 5: scale and operations

- durable queue and worker registry;
- multiple isolated Windows workers;
- capacity metrics, alerts, worker quarantine, and automated VM recycle;
- operational runbooks.

## Documentation model

The RFC is the durable source of architecture decisions and tradeoffs. GitHub issues track executable work. A single giant issue would mix design, implementation, dependencies, testing, and operations and would become stale.

Use:

- one roadmap/epic issue linking the RFC and all workstreams;
- separate issues for contract/control plane, file backends, Path A supervisor, Path C add-in, validation/security, and test/operations;
- draft PRs for reviewable design or implementation changes;
- Architecture Decision Records or RFC amendments when a major decision changes;
- milestones or GitHub Projects later if scheduling and ownership require them.

## Open decisions before implementation

1. Excel-DNA versus VSTO for the first Path C proof of concept. Default: Excel-DNA.
2. One Excel process per job versus controlled warm process reuse. Default: one process per job until soak data supports reuse.
3. Whether Aspose.Cells is worth licensing after benchmark and fidelity tests.
4. Whether Open XML SDK helpers live inside the supervisor repository subtree or a separate runtime package.
5. Queue technology for multi-worker operation. Defer until a single-worker runtime is reliable.
6. Code-signing certificate and release distribution model.

## Acceptance criteria for this RFC

- Maintainer accepts or amends the architectural decisions.
- Implementation issues reference this document and have bounded acceptance criteria.
- No implementation claims `success` solely because `RefreshAll`, calculation, or save returned.
- Path C cannot ship without external supervision and workbook-contract validation.
- Path A cannot remain the default after Path C passes certification and soak requirements.
