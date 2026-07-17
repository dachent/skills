"""Read-only OOXML package inspection for file-backend routing (issue #35).

`inspect_workbook` never opens the file with openpyxl and never touches
Excel COM. Per RFC 0001's "File-backend routing" section, a workbook's
feature inventory has to be trustworthy *before* deciding which library, if
any, is safe to open it with -- asking openpyxl's own object model whether a
workbook is safe is circular, because openpyxl might already be the wrong
tool to have opened it with. So this module reads the raw OOXML package
(zipfile + minimal namespace-agnostic XML parsing) instead.

Detection is deliberately narrow and matches only the fields the single-user
descope (RFC 0002) actually routes on: macros, digital signatures, external
links, a Data Model part, pivot caches, slicer caches, and embedded objects.
The original issue's full inventory (drawings, queries/connections,
add-in dependencies, calculation settings, edit volume/shape) is out of
scope here -- see the module docstring in file_router.py and the xlsx-win/v2
README for the descope rationale.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

# .xlsx/.xlsm are OOXML zip packages this module inspects directly. .xls is
# the legacy binary format (not a zip at all); .csv/.tsv are plain delimited
# text. All three are detected by extension only -- there is no OOXML
# package to open, so no deeper inventory is possible or meaningful.
_SHALLOW_FORMATS = frozenset({"xls", "csv", "tsv"})
_OOXML_FORMATS = frozenset({"xlsx", "xlsm"})

_EXTENSION_TO_FORMAT = {
    ".xlsx": "xlsx",
    ".xlsm": "xlsm",
    ".xls": "xls",
    ".csv": "csv",
    ".tsv": "tsv",
}

# Zip entries that, if present, positively indicate the corresponding risk
# feature. Prefix-matched (case-insensitive) against the package namelist,
# except _VBA_PROJECT_ENTRY which is matched exactly. These are the OOXML
# package locations named in issue #35: xl/vbaProject.bin, an
# OPC digital-signature origin part, xl/externalLinks, the Power Pivot Data
# Model part group (xl/model/), xl/pivotCache, xl/slicerCaches, and
# xl/embeddings.
_VBA_PROJECT_ENTRY = "xl/vbaproject.bin"
_SIGNATURE_PREFIX = "_xmlsignatures/"
_EXTERNAL_LINKS_PREFIX = "xl/externallinks/"
_DATA_MODEL_PREFIX = "xl/model/"
_PIVOT_CACHE_PREFIX = "xl/pivotcache/"
_SLICER_CACHE_PREFIX = "xl/slicercaches/"
_EMBEDDINGS_PREFIX = "xl/embeddings/"

_CONTENT_TYPES_ENTRY = "[Content_Types].xml"

# zipfile.BadZipFile covers "not a zip at all"; the others cover a valid zip
# that isn't a well-formed OOXML package (missing/garbled parts we try to
# read). Every one of these must fail closed (is_classifiable=False), never
# propagate as an unhandled exception.
_DETECTION_FAILURE_EXCEPTIONS = (zipfile.BadZipFile, KeyError, ET.ParseError, OSError)


@dataclass(frozen=True)
class WorkbookInventory:
    """A workbook's routing-relevant feature inventory.

    `is_classifiable` is False when the package could not be positively
    identified as a well-formed OOXML file at all (corrupt zip, missing
    `[Content_Types].xml`, ...) despite an xlsx/xlsm extension. Every other
    boolean field defaults to False, meaning "not detected" -- for a shallow
    format (.xls/.csv/.tsv) or an unclassifiable package, "not detected" is
    not the same claim as "confirmed absent", which is exactly why the
    router (file_router.py) treats file_format and is_classifiable as
    gating checks rather than trusting the risk flags alone in those cases.
    """

    path: str
    exists: bool
    file_format: str
    sheet_count: int = 0
    has_macros: bool = False
    is_signed: bool = False
    has_external_links: bool = False
    has_data_model: bool = False
    has_pivots: bool = False
    has_slicers: bool = False
    has_embedded_objects: bool = False
    is_classifiable: bool = True


def _detect_file_format(path: Path) -> str:
    return _EXTENSION_TO_FORMAT.get(path.suffix.lower(), path.suffix.lower().lstrip("."))


def _has_prefix(namelist: list, prefix: str) -> bool:
    return any(name.lower().startswith(prefix) for name in namelist)


def _has_exact(namelist: list, entry: str) -> bool:
    return any(name.lower() == entry for name in namelist)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _count_sheets(zf: zipfile.ZipFile) -> int:
    root = ET.fromstring(zf.read("xl/workbook.xml"))
    return sum(1 for element in root.iter() if _local_name(element.tag) == "sheet")


def _inspect_ooxml_package(path: Path, file_format: str) -> WorkbookInventory:
    try:
        with zipfile.ZipFile(path) as zf:
            namelist = zf.namelist()
            if _CONTENT_TYPES_ENTRY not in namelist:
                # A valid zip, but not an OOXML package -- can't be trusted.
                return WorkbookInventory(
                    path=str(path), exists=True, file_format=file_format, is_classifiable=False
                )

            return WorkbookInventory(
                path=str(path),
                exists=True,
                file_format=file_format,
                sheet_count=_count_sheets(zf),
                has_macros=_has_exact(namelist, _VBA_PROJECT_ENTRY),
                is_signed=_has_prefix(namelist, _SIGNATURE_PREFIX),
                has_external_links=_has_prefix(namelist, _EXTERNAL_LINKS_PREFIX),
                has_data_model=_has_prefix(namelist, _DATA_MODEL_PREFIX),
                has_pivots=_has_prefix(namelist, _PIVOT_CACHE_PREFIX),
                has_slicers=_has_prefix(namelist, _SLICER_CACHE_PREFIX),
                has_embedded_objects=_has_prefix(namelist, _EMBEDDINGS_PREFIX),
            )
    except _DETECTION_FAILURE_EXCEPTIONS:
        # Fail closed rather than raise: an xlsx/xlsm-named file that can't
        # be positively classified is unclassifiable, not "safe by default".
        return WorkbookInventory(
            path=str(path), exists=True, file_format=file_format, is_classifiable=False
        )


def inspect_workbook(path: str | Path) -> WorkbookInventory:
    """Inspect a workbook path and return its routing-relevant feature inventory.

    Never raises for a missing, corrupt, or unrecognized file -- a
    nonexistent path (new-workbook intent) reports `exists=False`, and a
    file that can't be opened as a valid OOXML package despite an
    xlsx/xlsm extension reports `is_classifiable=False` instead of
    propagating an exception. Never imports or invokes openpyxl.
    """
    resolved = Path(path)
    file_format = _detect_file_format(resolved)

    if not resolved.exists():
        return WorkbookInventory(path=str(resolved), exists=False, file_format=file_format)

    if file_format in _SHALLOW_FORMATS:
        # .xls/.csv/.tsv are not OOXML zips -- extension/signature only.
        return WorkbookInventory(path=str(resolved), exists=True, file_format=file_format)

    if file_format in _OOXML_FORMATS:
        return _inspect_ooxml_package(resolved, file_format)

    # Unrecognized extension: neither a known OOXML format nor a known
    # shallow format. Report what we know (nothing further) and let the
    # router's fail-closed default handle it -- guessing here would be the
    # same mistake the router itself is built to avoid.
    return WorkbookInventory(path=str(resolved), exists=True, file_format=file_format)
