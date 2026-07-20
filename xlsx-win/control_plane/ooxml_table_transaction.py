"""Allowlisted streaming worksheet rewrite for composite Table operations.

The intermediate package changes exactly one worksheet part. Table and Pivot
definitions, caches, records, relationships, styles, drawings, calculation
parts, and every unrelated byte stream stay content-identical. Native Excel
subsequently owns ListObject.Resize, calculated-column fill, Pivot refresh,
save, and fresh-reopen verification.
"""

from __future__ import annotations

import copy
import hashlib
import json
import posixpath
import re
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from .errors import ContractError
from .table_sidecar import iter_typed_rows, load_sidecar_schema

MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL = "http://schemas.openxmlformats.org/package/2006/relationships"
XML = "http://www.w3.org/XML/1998/namespace"
NS = {"m": MAIN, "r": REL, "p": PKG_REL}

_CELL_RE = re.compile(r"^\$?([A-Z]{1,3})\$?([1-9][0-9]*)$")
_RANGE_RE = re.compile(r"^\$?([A-Z]{1,3})\$?([1-9][0-9]*):\$?([A-Z]{1,3})\$?([1-9][0-9]*)$")


@dataclass(frozen=True)
class PackagePreflight:
    workbook_part: str
    worksheet_part: str
    table_part: str
    table_ref: str
    sheet_name: str
    table_name: str
    header_row: int
    body_start_row: int
    old_body_end_row: int
    final_body_end_row: int
    first_column: int
    last_column: int
    style_ids: tuple[str | None, ...]
    linked_cache_parts: tuple[str, ...]
    linked_pivot_parts: tuple[str, ...]
    part_sha256_before: dict[str, str]

    def to_dict(self) -> dict:
        return {
            "workbook_part": self.workbook_part,
            "worksheet_part": self.worksheet_part,
            "table_part": self.table_part,
            "table_ref": self.table_ref,
            "sheet_name": self.sheet_name,
            "table_name": self.table_name,
            "header_row": self.header_row,
            "body_start_row": self.body_start_row,
            "old_body_end_row": self.old_body_end_row,
            "final_body_end_row": self.final_body_end_row,
            "first_column": self.first_column,
            "last_column": self.last_column,
            "style_ids": list(self.style_ids),
            "linked_cache_parts": list(self.linked_cache_parts),
            "linked_pivot_parts": list(self.linked_pivot_parts),
            "part_sha256_before": self.part_sha256_before,
        }


def _sha256_stream(stream) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def _part_hashes(package: zipfile.ZipFile) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for info in package.infolist():
        if info.is_dir():
            continue
        with package.open(info, "r") as stream:
            hashes[info.filename] = _sha256_stream(stream)
    return hashes


def _relationships(package: zipfile.ZipFile, source_part: str) -> dict[str, str]:
    folder, name = posixpath.split(source_part)
    rels_part = posixpath.join(folder, "_rels", f"{name}.rels")
    try:
        root = etree.fromstring(package.read(rels_part))
    except (KeyError, etree.XMLSyntaxError) as exc:
        raise ContractError(
            "PACKAGE_PREFLIGHT_INVALID", "Required relationship part is missing or malformed.", {"part": rels_part}
        ) from exc
    result: dict[str, str] = {}
    for relationship in root.findall("p:Relationship", NS):
        if relationship.get("TargetMode") == "External":
            continue
        target = relationship.get("Target")
        relationship_id = relationship.get("Id")
        if target and relationship_id:
            if target.startswith("/"):
                resolved = target.lstrip("/")
            else:
                resolved = posixpath.normpath(posixpath.join(folder, target))
            result[relationship_id] = resolved
    return result


def _column_number(letters: str) -> int:
    value = 0
    for character in letters:
        value = value * 26 + ord(character) - 64
    return value


def _column_letters(number: int) -> str:
    letters = ""
    while number:
        number, remainder = divmod(number - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def _parse_cell(reference: str) -> tuple[int, int]:
    match = _CELL_RE.fullmatch(reference.upper())
    if not match:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Invalid A1 cell reference.", {"reference": reference})
    return _column_number(match.group(1)), int(match.group(2))


def _parse_range(reference: str) -> tuple[int, int, int, int]:
    match = _RANGE_RE.fullmatch(reference.upper())
    if not match:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Invalid A1 range reference.", {"reference": reference})
    return (
        _column_number(match.group(1)),
        int(match.group(2)),
        _column_number(match.group(3)),
        int(match.group(4)),
    )


def _ranges_intersect(left: tuple[int, int, int, int], right: tuple[int, int, int, int]) -> bool:
    return not (left[2] < right[0] or right[2] < left[0] or left[3] < right[1] or right[3] < left[1])


def _find_sheet_part(package: zipfile.ZipFile, workbook: etree._Element, sheet_name: str) -> str:
    rels = _relationships(package, "xl/workbook.xml")
    matches = [sheet for sheet in workbook.findall("m:sheets/m:sheet", NS) if sheet.get("name") == sheet_name]
    if len(matches) != 1:
        raise ContractError(
            "PACKAGE_PREFLIGHT_INVALID", "Target worksheet must resolve exactly once.", {"sheet": sheet_name, "matches": len(matches)}
        )
    relationship_id = matches[0].get(f"{{{REL}}}id")
    if relationship_id not in rels:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Target worksheet relationship is unresolved.", {"rid": relationship_id})
    return rels[relationship_id]


def _find_table_part(package: zipfile.ZipFile, worksheet_part: str, table_name: str) -> tuple[str, etree._Element]:
    rels = _relationships(package, worksheet_part)
    candidates: list[tuple[str, etree._Element]] = []
    for part in rels.values():
        if not part.lower().startswith("xl/tables/"):
            continue
        try:
            root = etree.fromstring(package.read(part))
        except (KeyError, etree.XMLSyntaxError):
            continue
        if root.get("name") == table_name or root.get("displayName") == table_name:
            candidates.append((part, root))
    if len(candidates) != 1:
        raise ContractError(
            "PACKAGE_PREFLIGHT_INVALID", "Target Table must resolve exactly once.", {"table": table_name, "matches": len(candidates)}
        )
    return candidates[0]


def _saved_sort(table: etree._Element, column_names: list[str]) -> dict | None:
    auto_filter = table.find("m:autoFilter", NS)
    if auto_filter is None:
        return None
    if auto_filter.findall("m:filterColumn", NS):
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Active Table filters are outside the initial profile.", {})
    sort_state = table.find("m:sortState", NS)
    if sort_state is None:
        sort_state = auto_filter.find("m:sortState", NS)
    if sort_state is None:
        return None
    conditions = sort_state.findall("m:sortCondition", NS)
    if len(conditions) != 1:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Exactly one saved sort condition is supported.", {})
    condition_ref = conditions[0].get("ref")
    if not condition_ref:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Saved sort condition has no range.", {})
    first_col, _first_row, last_col, _last_row = _parse_range(condition_ref)
    if first_col != last_col:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Saved sort must target one Table column.", {"ref": condition_ref})
    table_first, _, _, _ = _parse_range(table.get("ref"))
    index = first_col - table_first
    if index < 0 or index >= len(column_names):
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Saved sort column is outside the target Table.", {"ref": condition_ref})
    return {
        "column": column_names[index],
        "direction": "descending" if conditions[0].get("descending") in {"1", "true"} else "ascending",
        "behavior": "preserve_descriptor_do_not_reapply",
    }


def _linked_pivots(package: zipfile.ZipFile, workbook: etree._Element, table_name: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    workbook_rels = _relationships(package, "xl/workbook.xml")
    linked_cache_ids: dict[str, str] = {}
    for cache in workbook.findall("m:pivotCaches/m:pivotCache", NS):
        relationship_id = cache.get(f"{{{REL}}}id")
        cache_id = cache.get("cacheId")
        if relationship_id not in workbook_rels or cache_id is None:
            continue
        cache_part = workbook_rels[relationship_id]
        try:
            definition = etree.fromstring(package.read(cache_part))
        except (KeyError, etree.XMLSyntaxError) as exc:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Pivot cache definition is missing or malformed.", {"part": cache_part}) from exc
        cache_source = definition.find("m:cacheSource", NS)
        worksheet_source = definition.find("m:cacheSource/m:worksheetSource", NS)
        if cache_source is not None and cache_source.get("type") == "worksheet" and worksheet_source is not None and worksheet_source.get("name") == table_name:
            linked_cache_ids[cache_id] = cache_part

    linked_reports: list[str] = []
    for part in package.namelist():
        if not part.lower().startswith("xl/pivottables/pivottable") or not part.lower().endswith(".xml"):
            continue
        try:
            report = etree.fromstring(package.read(part))
        except etree.XMLSyntaxError as exc:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Pivot report definition is malformed.", {"part": part}) from exc
        if report.get("cacheId") in linked_cache_ids:
            linked_reports.append(part)
    return tuple(sorted(set(linked_cache_ids.values()))), tuple(sorted(linked_reports))


def _sheet_preflight(
    package: zipfile.ZipFile,
    worksheet_part: str,
    *,
    template_row: int,
    first_column: int,
    last_column: int,
    collision_range: tuple[int, int, int, int] | None,
) -> tuple[tuple[str | None, ...], list[dict]]:
    style_ids: dict[int, str | None] = {}
    collisions: list[dict] = []
    unsupported: list[dict] = []
    with package.open(worksheet_part, "r") as stream:
        try:
            for _event, element in etree.iterparse(stream, events=("end",), huge_tree=True):
                local = etree.QName(element).localname
                if local == "row":
                    row_number = int(element.get("r", "0"))
                    for cell in element.findall(f"{{{MAIN}}}c"):
                        reference = cell.get("r")
                        if not reference:
                            continue
                        column, row = _parse_cell(reference)
                        if row_number == template_row:
                            style_ids[column] = cell.get("s")
                        if collision_range and _ranges_intersect((column, row, column, row), collision_range):
                            collisions.append({"cell": reference})
                    element.clear()
                elif local in {"mergeCell", "conditionalFormatting", "dataValidation"} and collision_range:
                    references = element.get("ref") or element.get("sqref") or ""
                    for reference in references.split():
                        try:
                            parsed = _parse_range(reference) if ":" in reference else (*_parse_cell(reference), *_parse_cell(reference))
                            if len(parsed) == 4 and _ranges_intersect(parsed, collision_range):
                                unsupported.append({"feature": local, "ref": reference})
                        except ContractError:
                            unsupported.append({"feature": local, "ref": reference})
                elif local in {"drawing", "legacyDrawing", "oleObjects", "controls"} and collision_range:
                    unsupported.append({"feature": local, "reason": "anchor analysis is outside initial profile"})
        except (etree.XMLSyntaxError, OSError, ValueError) as exc:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Target worksheet is malformed.", {"part": worksheet_part}) from exc
    if unsupported:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Unsupported artifacts intersect or obscure the mutation delta.", {"artifacts": unsupported})
    if collisions:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Growth rectangle is not blank.", {"collisions": collisions[:25], "count": len(collisions)})
    return tuple(style_ids.get(column) for column in range(first_column, last_column + 1)), collisions


def preflight_package(workbook_path: str | Path, operation: dict, sidecar_schema: dict) -> PackagePreflight:
    path = Path(workbook_path)
    if path.suffix.lower() != ".xlsx":
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Only .xlsx packages are supported.", {"path": str(path)})
    try:
        package = zipfile.ZipFile(path, "r")
    except (OSError, zipfile.BadZipFile) as exc:
        raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Workbook is not a readable OOXML package.", {"path": str(path)}) from exc
    with package:
        names_lower = {name.lower() for name in package.namelist()}
        forbidden = [
            name for name in names_lower
            if name.startswith("_xmlsignatures/")
            or name.startswith("xl/externallinks/")
            or name.startswith("xl/model/")
            or name.startswith("xl/slicercaches/")
            or name.startswith("xl/embeddings/")
            or name == "xl/connections.xml"
            or name == "xl/vbaproject.bin"
        ]
        if forbidden:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Workbook contains an unsupported package feature.", {"parts": sorted(forbidden)})
        try:
            workbook = etree.fromstring(package.read("xl/workbook.xml"))
        except (KeyError, etree.XMLSyntaxError) as exc:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Workbook definition is missing or malformed.", {}) from exc

        table_contract = operation["table"]
        worksheet_part = _find_sheet_part(package, workbook, table_contract["sheet"])
        table_part, table = _find_table_part(package, worksheet_part, table_contract["name"])
        table_ref = table.get("ref")
        if not table_ref:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Target Table has no range.", {"table": table_contract["name"]})
        first_col, header_row, last_col, old_end = _parse_range(table_ref)
        actual_body_rows = old_end - header_row
        column_nodes = table.findall("m:tableColumns/m:tableColumn", NS)
        column_names = [node.get("name") or "" for node in column_nodes]
        expected_names = [column["name"] for column in table_contract["columns"]]
        sidecar_names = [column["name"] for column in sidecar_schema["columns"]]
        failures: list[dict] = []
        if table.get("totalsRowShown", "0") not in {"0", "false"} or table_contract["totals"] is not False:
            failures.append({"check": "totals_disabled"})
        if actual_body_rows != table_contract["existing_body_rows"]:
            failures.append({"check": "existing_body_rows", "actual": actual_body_rows, "expected": table_contract["existing_body_rows"]})
        if last_col - first_col + 1 != table_contract["column_count"]:
            failures.append({"check": "column_count", "actual": last_col - first_col + 1, "expected": table_contract["column_count"]})
        if column_names != expected_names or sidecar_names != expected_names:
            failures.append({"check": "column_identity", "table": column_names, "manifest": expected_names, "sidecar": sidecar_names})
        for manifest_column, sidecar_column, table_column in zip(table_contract["columns"], sidecar_schema["columns"], column_nodes):
            if manifest_column["role"] != sidecar_column["role"] or manifest_column["logical_type"] != sidecar_column["logical_type"]:
                failures.append({"check": "typed_column", "column": manifest_column["name"]})
            has_formula = table_column.find("m:calculatedColumnFormula", NS) is not None
            if has_formula != (manifest_column["role"] == "calculated"):
                failures.append({"check": "calculated_column", "column": manifest_column["name"], "has_formula": has_formula})
        observed_sort = _saved_sort(table, column_names)
        if observed_sort != table_contract.get("saved_sort"):
            failures.append({"check": "saved_sort", "actual": observed_sort, "expected": table_contract.get("saved_sort")})

        linked_caches, linked_reports = _linked_pivots(package, workbook, table_contract["name"])
        pivot_contract = operation["dependent_pivots"]
        if len(linked_caches) != pivot_contract["cache_count"] or len(linked_reports) != pivot_contract["report_count"]:
            failures.append(
                {
                    "check": "pivot_topology",
                    "actual_cache_count": len(linked_caches),
                    "actual_report_count": len(linked_reports),
                    "expected_cache_count": pivot_contract["cache_count"],
                    "expected_report_count": pivot_contract["report_count"],
                }
            )
        if failures:
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Raw OOXML graph does not match the immutable transaction contract.", {"failures": failures})

        final_end = header_row + table_contract["final_body_rows"]
        collision_range = None
        if final_end > old_end:
            collision_range = (first_col, old_end + 1, last_col, final_end)
        template_styles, _ = _sheet_preflight(
            package,
            worksheet_part,
            template_row=header_row + 1,
            first_column=first_col,
            last_column=last_col,
            collision_range=collision_range,
        )
        if not template_styles or len(template_styles) != len(column_nodes):
            raise ContractError("PACKAGE_PREFLIGHT_INVALID", "Cannot bind per-column template styles from the first Table body row.", {})
        return PackagePreflight(
            workbook_part="xl/workbook.xml",
            worksheet_part=worksheet_part,
            table_part=table_part,
            table_ref=table_ref,
            sheet_name=table_contract["sheet"],
            table_name=table_contract["name"],
            header_row=header_row,
            body_start_row=header_row + 1,
            old_body_end_row=old_end,
            final_body_end_row=final_end,
            first_column=first_col,
            last_column=last_col,
            style_ids=template_styles,
            linked_cache_parts=linked_caches,
            linked_pivot_parts=linked_reports,
            part_sha256_before=_part_hashes(package),
        )


def _new_cell(cell, column_number: int, row_number: int, style_id: str | None) -> etree._Element | None:
    if cell.role != "writable" or cell.normalized is None:
        return None
    attributes = {"r": f"{_column_letters(column_number)}{row_number}"}
    if style_id is not None:
        attributes["s"] = style_id
    element = etree.Element(f"{{{MAIN}}}c", attributes)
    if cell.storage_type == "inline_string":
        element.set("t", "inlineStr")
        inline = etree.SubElement(element, f"{{{MAIN}}}is")
        text = etree.SubElement(inline, f"{{{MAIN}}}t")
        if cell.ooxml_value != cell.ooxml_value.strip():
            text.set(f"{{{XML}}}space", "preserve")
        text.text = cell.ooxml_value
    else:
        if cell.storage_type == "boolean":
            element.set("t", "b")
        value = etree.SubElement(element, f"{{{MAIN}}}v")
        value.text = cell.ooxml_value
    return element


def _cell_column(element: etree._Element) -> int:
    reference = element.get("r")
    return _parse_cell(reference)[0] if reference else 0


def _transform_target_row(
    row: etree._Element | None,
    typed_cells: list,
    row_number: int,
    preflight: PackagePreflight,
) -> etree._Element:
    if row is None:
        row = etree.Element(f"{{{MAIN}}}row", {"r": str(row_number)})
    existing_styles: dict[int, str | None] = {}
    for child in list(row):
        if etree.QName(child).localname != "c":
            continue
        column = _cell_column(child)
        if preflight.first_column <= column <= preflight.last_column:
            existing_styles[column] = child.get("s")
            role = typed_cells[column - preflight.first_column].role
            if role == "writable":
                row.remove(child)
    for offset, typed_cell in enumerate(typed_cells):
        column = preflight.first_column + offset
        style_id = existing_styles.get(column, preflight.style_ids[offset])
        new_cell = _new_cell(typed_cell, column, row_number, style_id)
        if new_cell is not None:
            row.append(new_cell)
    cells = [child for child in row if etree.QName(child).localname == "c"]
    for child in cells:
        row.remove(child)
    for child in sorted(cells, key=_cell_column):
        row.insert(len([entry for entry in row if etree.QName(entry).localname == "c"]), child)
    return row


def _clear_owned_tail(row: etree._Element, preflight: PackagePreflight) -> etree._Element:
    for child in list(row):
        if etree.QName(child).localname == "c":
            column = _cell_column(child)
            if preflight.first_column <= column <= preflight.last_column:
                row.remove(child)
    return row


def _rewrite_sheet(
    source_stream,
    destination_path: Path,
    operation: dict,
    sidecar_schema: dict,
    preflight: PackagePreflight,
) -> None:
    source_rows = iter(iter_typed_rows(operation["source"]["path"], sidecar_schema))
    target_start = (
        preflight.old_body_end_row + 1
        if operation["type"] == "append_table_rows"
        else preflight.body_start_row
    )
    target_end = preflight.final_body_end_row
    next_target = target_start
    sheet_data_context = None
    root_context = None
    root = None
    seen_sheet_data = False

    with etree.xmlfile(str(destination_path), encoding="UTF-8") as output:
        output.write_declaration(standalone=True)
        for event, element in etree.iterparse(source_stream, events=("start", "end"), huge_tree=True):
            parent = element.getparent()
            local = etree.QName(element).localname
            if root is None and event == "start":
                root = element
                root_context = output.element(root.tag, dict(root.attrib), nsmap=root.nsmap)
                root_context.__enter__()
                continue
            if event == "start" and parent is root and local == "sheetData":
                seen_sheet_data = True
                sheet_data_context = output.element(element.tag, dict(element.attrib), nsmap=element.nsmap)
                sheet_data_context.__enter__()
                continue
            if event != "end":
                continue
            if local == "row" and element.getparent() is not None and etree.QName(element.getparent()).localname == "sheetData":
                current_row = int(element.get("r", "0"))
                while next_target <= target_end and next_target < current_row:
                    try:
                        typed = next(source_rows)
                    except StopIteration as exc:
                        raise ContractError("PACKAGE_REWRITE_FAILED", "CSV ended before the declared source row count.", {}) from exc
                    output.write(_transform_target_row(None, typed, next_target, preflight))
                    next_target += 1
                if target_start <= current_row <= target_end:
                    try:
                        typed = next(source_rows)
                    except StopIteration as exc:
                        raise ContractError("PACKAGE_REWRITE_FAILED", "CSV ended before the declared source row count.", {}) from exc
                    output.write(_transform_target_row(element, typed, current_row, preflight))
                    next_target = current_row + 1
                elif operation["type"] == "replace_table_data" and target_end < current_row <= preflight.old_body_end_row:
                    output.write(_clear_owned_tail(element, preflight))
                else:
                    output.write(element)
                element.clear()
                while element.getprevious() is not None:
                    del element.getparent()[0]
                continue
            if parent is root and local == "sheetData":
                while next_target <= target_end:
                    try:
                        typed = next(source_rows)
                    except StopIteration as exc:
                        raise ContractError("PACKAGE_REWRITE_FAILED", "CSV ended before the declared source row count.", {}) from exc
                    output.write(_transform_target_row(None, typed, next_target, preflight))
                    next_target += 1
                try:
                    next(source_rows)
                    raise ContractError("PACKAGE_REWRITE_FAILED", "CSV contains more rows than the declared source row count.", {})
                except StopIteration:
                    pass
                sheet_data_context.__exit__(None, None, None)
                sheet_data_context = None
                element.clear()
                continue
            if parent is root:
                if local == "dimension":
                    start_col, start_row, end_col, end_row = _parse_range(element.get("ref"))
                    end_col = max(end_col, preflight.last_column)
                    end_row = max(end_row, preflight.final_body_end_row)
                    element.set("ref", f"{_column_letters(start_col)}{start_row}:{_column_letters(end_col)}{end_row}")
                output.write(element)
                element.clear()
            if element is root:
                break
        if not seen_sheet_data or root_context is None:
            raise ContractError("PACKAGE_REWRITE_FAILED", "Target worksheet has no sheetData element.", {})
        root_context.__exit__(None, None, None)


def _rewrite_table_definition(table_xml: bytes, preflight: PackagePreflight) -> bytes:
    root = etree.fromstring(table_xml)
    final_ref = (
        f"{_column_letters(preflight.first_column)}{preflight.header_row}:"
        f"{_column_letters(preflight.last_column)}{preflight.final_body_end_row}"
    )
    root.set("ref", final_ref)

    def extend(node: etree._Element) -> None:
        reference = node.get("ref")
        if not reference:
            return
        first_col, first_row, last_col, _last_row = _parse_range(reference)
        node.set(
            "ref",
            f"{_column_letters(first_col)}{first_row}:{_column_letters(last_col)}{preflight.final_body_end_row}",
        )

    auto_filter = root.find("m:autoFilter", NS)
    if auto_filter is not None:
        extend(auto_filter)
    sort_state = root.find("m:sortState", NS)
    if sort_state is not None:
        extend(sort_state)
        for condition in sort_state.findall("m:sortCondition", NS):
            extend(condition)
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True, standalone=True)


def rewrite_intermediate_package(
    workbook_path: str | Path,
    output_path: str | Path,
    operation: dict,
    sidecar_schema: dict,
    preflight: PackagePreflight,
) -> dict:
    source_path = Path(workbook_path)
    destination_path = Path(output_path)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xlsx-win-ooxml-") as temporary:
        rewritten_sheet = Path(temporary) / "sheet.xml"
        try:
            with zipfile.ZipFile(source_path, "r") as source_package:
                rewritten_table = _rewrite_table_definition(source_package.read(preflight.table_part), preflight)
                with source_package.open(preflight.worksheet_part, "r") as source_sheet:
                    _rewrite_sheet(source_sheet, rewritten_sheet, operation, sidecar_schema, preflight)
                with zipfile.ZipFile(destination_path, "w", allowZip64=True) as destination_package:
                    for info in source_package.infolist():
                        target_info = copy.copy(info)
                        if info.is_dir():
                            destination_package.writestr(target_info, b"")
                            continue
                        with destination_package.open(target_info, "w", force_zip64=True) as target_stream:
                            if info.filename == preflight.worksheet_part:
                                with rewritten_sheet.open("rb") as replacement_stream:
                                    shutil.copyfileobj(replacement_stream, target_stream, length=1024 * 1024)
                            elif info.filename == preflight.table_part:
                                target_stream.write(rewritten_table)
                            else:
                                with source_package.open(info, "r") as original_stream:
                                    shutil.copyfileobj(original_stream, target_stream, length=1024 * 1024)
        except ContractError:
            raise
        except (OSError, zipfile.BadZipFile, etree.XMLSyntaxError) as exc:
            raise ContractError("PACKAGE_REWRITE_FAILED", "Failed to build the allowlisted intermediate package.", {"error": str(exc)}) from exc

    with zipfile.ZipFile(destination_path, "r") as result_package:
        after = _part_hashes(result_package)
    before = preflight.part_sha256_before
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    changed = sorted(part for part in before.keys() & after.keys() if before[part] != after[part])
    allowed = sorted([preflight.table_part, preflight.worksheet_part])
    if added or removed or changed != allowed:
        try:
            destination_path.unlink()
        except OSError:
            pass
        raise ContractError(
            "PACKAGE_REWRITE_FAILED",
            "Intermediate package escaped the worksheet/Table allowlist.",
            {"added": added, "removed": removed, "changed": changed, "allowed": allowed},
        )
    return {
        "schema_version": "1.0",
        "candidate": "streaming_ooxml_native_excel_v1",
        "allowed_changed_parts": allowed,
        "changed_parts": changed,
        "added_parts": added,
        "removed_parts": removed,
        "before": before,
        "after": after,
    }
