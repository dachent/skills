"""Deterministic file-backend routing for issue #35 (single-user descope).

RFC 0001's "File-backend routing" section lists a full matrix of workloads
against candidate engines (XlsxWriter, PyExcelerate, pandas/Polars,
fastexcel/calamine, openpyxl, a targeted OOXML patcher, Open XML SDK,
Aspose.Cells, Path C bulk writes). RFC 0002 (the single-user scope amendment)
trims that to what a one-person desktop deployment actually needs, without
evaluating or benchmarking the rest of the matrix up front:

- ``xlsxwriter`` -- new workbook creation with no existing file to preserve.
- ``openpyxl`` -- editing an existing plain xlsx/xlsm (no risk features).
- ``excel_required`` -- the fail-closed escape hatch: macros, signatures, a
  Data Model, pivots, slicers, embedded objects, external links, workbook
  connections (issue #70), or any workbook this router cannot positively
  classify as safe. RFC 0001 is explicit that a successful-looking edit is
  not evidence a workbook was safe to touch outside Excel, so this router
  never guesses.
- ``convert_required`` -- legacy binary .xls must become .xlsx before any
  Python-side edit; this router does not perform the conversion itself.
- ``not_applicable`` -- CSV/TSV, for any intent (creation or edit). These are
  plain delimited text, not an OOXML workbook, so this router declines to
  claim routing authority over them at all (see `_route_create_new` and
  `_route_edit_existing` below).

PyExcelerate, Aspose.Cells, fastexcel/calamine, and Open XML SDK are
explicitly out of scope for this issue. pandas is a data-shaping tool the
skill already uses (per SKILL.md), not a routing target this module chooses
between.

Routing is straight boolean logic over a `WorkbookInventory` -- no LLM
judgment, no heuristic scoring, no partial credit. Every branch either
matches an explicit rule below or falls through to the fail-closed default
at the bottom of `choose_backend`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .workbook_inventory import WorkbookInventory

CREATE_NEW = "create_new"
EDIT_EXISTING = "edit_existing"
CONVERT_FORMAT = "convert_format"
KNOWN_INTENTS = frozenset({CREATE_NEW, EDIT_EXISTING, CONVERT_FORMAT})

BACKEND_XLSXWRITER = "xlsxwriter"
BACKEND_OPENPYXL = "openpyxl"
BACKEND_EXCEL_REQUIRED = "excel_required"
BACKEND_CONVERT_REQUIRED = "convert_required"
BACKEND_NOT_APPLICABLE = "not_applicable"

# Inventory fields that, if any is True on an existing workbook, mean this
# router cannot prove the workbook is safe to open outside Excel. Order here
# is the order they're checked in, purely for stable/readable `explain`
# output -- it has no effect on the routing decision itself.
#
# has_connections (issue #70): a workbook connection (Power Query or legacy
# QueryTable/OLEDB/ODBC) is exactly the kind of feature SKILL.md's own
# existing guidance says must go through Excel COM, never file-only
# libraries -- so it fails closed here the same as the other seven fields,
# not just as a routing nicety.
_RISK_FIELDS = (
    "has_macros",
    "is_signed",
    "has_data_model",
    "has_pivots",
    "has_slicers",
    "has_embedded_objects",
    "has_external_links",
    "has_connections",
)


@dataclass(frozen=True)
class RouterDecision:
    """A routing decision: which backend, why, and the inventory fields that drove it.

    `explain` is always JSON-serializable on its own (str/bool/int values
    only) so a decision is inspectable without re-deriving it from the
    inventory -- the acceptance criterion this satisfies is "router
    decisions are deterministic and explainable in JSON," not just
    "printable."
    """

    backend: str
    reason: str
    explain: dict


def _decision(backend: str, reason: str, explain: dict) -> RouterDecision:
    return RouterDecision(backend=backend, reason=reason, explain=explain)


def _fail_closed(reason: str, explain: dict) -> RouterDecision:
    return _decision(BACKEND_EXCEL_REQUIRED, reason, explain)


def _triggered_risk_fields(inventory: WorkbookInventory) -> dict:
    return {field: True for field in _RISK_FIELDS if getattr(inventory, field)}


def _route_create_new(inventory: WorkbookInventory) -> RouterDecision:
    # Format check first, before the exists branch below: create_new is just
    # as format-blind a trap as edit_existing if xlsxwriter is handed a
    # csv/tsv/xls target just because inventory.exists happens to be False.
    # These checks apply regardless of exists, mirroring _route_edit_existing.
    if inventory.file_format in ("csv", "tsv"):
        return _decision(
            BACKEND_NOT_APPLICABLE,
            f".{inventory.file_format} is plain delimited text, not an OOXML workbook. Excel "
            "adds no fidelity value over a direct text write, but xlsxwriter (OOXML-only) is "
            "not a fit for producing a raw delimited file either. Routing this file type is "
            "out of this router's scope.",
            {"intent": CREATE_NEW, "file_format": inventory.file_format, "exists": inventory.exists},
        )

    if inventory.file_format == "xls":
        return _fail_closed(
            f"create_new was requested for a legacy binary .xls target ({inventory.path!r}); "
            "xlsxwriter cannot write the legacy binary format, and there is no existing file "
            "for a convert-then-edit path to apply to (that path is only meaningful for "
            "edit_existing). Target an .xlsx/.xlsm path instead, or create the file through "
            "Excel directly.",
            {"intent": CREATE_NEW, "file_format": "xls", "exists": inventory.exists},
        )

    if not inventory.exists:
        return _decision(
            BACKEND_XLSXWRITER,
            "No existing file to preserve; xlsxwriter is the fast path for new-workbook "
            "creation with no fidelity constraint from prior content.",
            {"intent": CREATE_NEW, "exists": False, "file_format": inventory.file_format},
        )
    return _fail_closed(
        f"create_new was requested but a file already exists at {inventory.path!r}; refusing "
        "to silently overwrite it through a file-creation library instead of an explicit "
        "edit/convert intent.",
        {"intent": CREATE_NEW, "exists": True, "file_format": inventory.file_format},
    )


def _route_edit_existing(inventory: WorkbookInventory) -> RouterDecision:
    if not inventory.exists:
        return _fail_closed(
            f"edit_existing was requested but no file exists at {inventory.path!r}.",
            {"intent": EDIT_EXISTING, "exists": False},
        )

    if inventory.file_format == "xls":
        return _decision(
            BACKEND_CONVERT_REQUIRED,
            "Legacy binary .xls must be converted to .xlsx before any Python-side edit; "
            "neither xlsxwriter nor openpyxl reads/writes the binary format.",
            {"intent": EDIT_EXISTING, "file_format": "xls"},
        )

    if inventory.file_format in ("csv", "tsv"):
        return _decision(
            BACKEND_NOT_APPLICABLE,
            f".{inventory.file_format} is plain delimited text, not an OOXML workbook. Excel "
            "adds no fidelity value over a direct text edit, but xlsxwriter (creation-only) and "
            "openpyxl (workbook-structure editing) are not a fit for editing a raw delimited "
            "file in place either. Routing this file type is out of this router's scope.",
            {"intent": EDIT_EXISTING, "file_format": inventory.file_format},
        )

    triggered = _triggered_risk_fields(inventory)
    if triggered:
        named = ", ".join(sorted(triggered))
        return _fail_closed(
            f"Workbook has feature(s) this router cannot positively classify as safe to edit "
            f"outside Excel: {named}. A successful-looking openpyxl edit would not be evidence "
            "the workbook was actually safe to touch this way (RFC 0001).",
            {"intent": EDIT_EXISTING, **triggered},
        )

    if inventory.file_format in ("xlsx", "xlsm"):
        return _decision(
            BACKEND_OPENPYXL,
            "Plain xlsx/xlsm with none of the tracked risk features detected; openpyxl "
            "preserves formulas, formatting, and structure for ordinary edits.",
            {
                "intent": EDIT_EXISTING,
                "file_format": inventory.file_format,
                **{field: False for field in _RISK_FIELDS},
            },
        )

    return _fail_closed(
        f"edit_existing was requested for file_format {inventory.file_format!r}, which no "
        "explicit routing rule covers.",
        {"intent": EDIT_EXISTING, "file_format": inventory.file_format},
    )


def choose_backend(intent: str, inventory: WorkbookInventory) -> RouterDecision:
    """Deterministically choose a file backend for `intent` given `inventory`.

    Raises ValueError if `intent` is not one of KNOWN_INTENTS -- that is a
    caller/programming error, not a routing outcome, so it is not
    represented as a RouterDecision (mirroring state_machine.py's ValueError
    for an unknown state name).

    Never guesses: an existing workbook that could not be positively
    classified as a well-formed OOXML package (`inventory.is_classifiable is
    False`) always routes to `excel_required`, regardless of intent, before
    any intent-specific rule runs.
    """
    if intent not in KNOWN_INTENTS:
        raise ValueError(f"Unknown intent: {intent!r}. Known intents: {sorted(KNOWN_INTENTS)}")

    if inventory.exists and not inventory.is_classifiable:
        return _fail_closed(
            "Workbook could not be positively classified as a well-formed OOXML package; "
            "failing closed rather than guessing it is safe to edit.",
            {"intent": intent, "is_classifiable": False, "file_format": inventory.file_format},
        )

    if intent == CREATE_NEW:
        return _route_create_new(inventory)

    if intent == EDIT_EXISTING:
        return _route_edit_existing(inventory)

    # CONVERT_FORMAT (and any future intent added to KNOWN_INTENTS without a
    # matching rule above) has no explicit rule in this issue's scope --
    # fail closed rather than defaulting into a file-editing library.
    return _fail_closed(
        f"No explicit routing rule for intent {intent!r} in this issue's scope; failing closed.",
        {"intent": intent},
    )
