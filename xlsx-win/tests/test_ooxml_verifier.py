from __future__ import annotations

import csv
import json
import zipfile

import pytest
from lxml import etree

from control_plane.errors import ContractError
from control_plane.ooxml_table_transaction import MAIN, preflight_package, rewrite_intermediate_package
from control_plane.ooxml_verifier import _matrix_hash, sha256_path, verify_final_package
from control_plane.table_sidecar import inspect_sidecar, load_sidecar_schema


def _seed_package(path) -> None:
    parts = {
        "[Content_Types].xml": '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>',
        "xl/workbook.xml": '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rSheet"/></sheets><pivotCaches><pivotCache cacheId="1" r:id="rCache"/></pivotCaches></workbook>',
        "xl/_rels/workbook.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rSheet" Target="worksheets/sheet1.xml"/><Relationship Id="rCache" Target="pivotCache/pivotCacheDefinition1.xml"/></Relationships>',
        "xl/worksheets/_rels/sheet1.xml.rels": '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rTable" Target="../tables/table1.xml"/></Relationships>',
        "xl/tables/table1.xml": '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="Data" displayName="Data" ref="B3:D5" totalsRowShown="0"><autoFilter ref="B3:D5"/><tableColumns count="3"><tableColumn id="1" name="Name"/><tableColumn id="2" name="Calc"><calculatedColumnFormula>[@Value]*2</calculatedColumnFormula></tableColumn><tableColumn id="3" name="Value"/></tableColumns></table>',
        "xl/pivotCache/pivotCacheDefinition1.xml": '<pivotCacheDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cacheSource type="worksheet"><worksheetSource name="Data"/></cacheSource></pivotCacheDefinition>',
        "xl/pivotTables/pivotTable1.xml": '<pivotTableDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" cacheId="1"/>',
        "xl/styles.xml": '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"/>',
        "xl/worksheets/sheet1.xml": '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><dimension ref="B3:Q5"/><sheetData><row r="1"><c r="Q1"><v>42</v></c></row><row r="3"><c r="B3" s="1" t="inlineStr"><is><t>Name</t></is></c><c r="C3" s="1" t="inlineStr"><is><t>Calc</t></is></c><c r="D3" s="1" t="inlineStr"><is><t>Value</t></is></c></row><row r="4"><c r="B4" s="1" t="inlineStr"><is><t>alpha</t></is></c><c r="C4" s="1"><f t="shared" si="0" ref="C4:C5">D4*2</f><v>2</v></c><c r="D4" s="1"><v>1</v></c></row><row r="5"><c r="B5" s="1" t="inlineStr"><is><t>beta</t></is></c><c r="C5" s="1"><f t="shared" si="0"/><v>4</v></c><c r="D5" s="1"><v>2</v></c></row></sheetData><tableParts count="1"><tablePart xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" r:id="rTable"/></tableParts></worksheet>',
    }
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as package:
        for name, data in parts.items():
            package.writestr(name, data)


def _operation_and_sidecar(tmp_path):
    schema = {
        "schema_version": "1.0",
        "encoding": "utf-8",
        "delimiter": ",",
        "quotechar": '"',
        "has_header": True,
        "date_system": "1900",
        "columns": [
            {"id": 1, "name": "Name", "role": "writable", "logical_type": "text", "storage_type": "inline_string", "number_format": None},
            {"id": 2, "name": "Calc", "role": "calculated", "logical_type": "number", "storage_type": "number", "number_format": None},
            {"id": 3, "name": "Value", "role": "writable", "logical_type": "number", "storage_type": "number", "number_format": None},
        ],
    }
    schema_path = tmp_path / "rows.schema.json"
    source_path = tmp_path / "rows.csv"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    with source_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["Name", "Calc", "Value"])
        writer.writerow(["gamma", "", "3"])
    stats = inspect_sidecar(source_path, schema_path, scratch_dir=tmp_path)
    operation = {
        "type": "append_table_rows",
        "version": "1",
        "table": {
            "sheet": "Data",
            "name": "Data",
            "existing_body_rows": 2,
            "final_body_rows": 3,
            "column_count": 3,
            "columns": [
                {"name": "Name", "role": "writable", "logical_type": "text"},
                {"name": "Calc", "role": "calculated", "logical_type": "number"},
                {"name": "Value", "role": "writable", "logical_type": "number"},
            ],
            "totals": False,
            "filters": "none",
            "saved_sort": None,
        },
        "source": {"path": str(source_path), "schema_path": str(schema_path), **stats.to_dict()},
        "dependent_pivots": {"cache_count": 1, "report_count": 1, "oracle_path": "pending", "oracle_sha256": "0" * 64},
    }
    return operation, load_sidecar_schema(schema_path)


def _simulate_native_excel(intermediate, output, *, move_table: bool = False, formula_exception: bool = False) -> None:
    with zipfile.ZipFile(intermediate, "r") as source, zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as target:
        for info in source.infolist():
            data = source.read(info.filename)
            if info.filename == "xl/tables/table1.xml":
                root = etree.fromstring(data)
                root.set("ref", "C3:E6" if move_table else "B3:D6")
                root.find(f"{{{MAIN}}}autoFilter").set("ref", "C3:E6" if move_table else "B3:D6")
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "xl/worksheets/sheet1.xml":
                root = etree.fromstring(data)
                row4 = root.find(f".//{{{MAIN}}}row[@r='4']")
                row4.find(f"{{{MAIN}}}c[@r='C4']/{{{MAIN}}}f").set("ref", "C4:C6")
                if formula_exception:
                    row5 = root.find(f".//{{{MAIN}}}row[@r='5']")
                    formula = row5.find(f"{{{MAIN}}}c[@r='C5']/{{{MAIN}}}f")
                    formula.attrib.clear()
                    formula.text = "D5*3"
                row6 = root.find(f".//{{{MAIN}}}row[@r='6']")
                formula_cell = etree.Element(f"{{{MAIN}}}c", r="C6", s="1")
                formula = etree.SubElement(formula_cell, f"{{{MAIN}}}f", t="shared", si="0")
                row6.insert(1, formula_cell)
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "xl/pivotCache/pivotCacheDefinition1.xml":
                root = etree.fromstring(data)
                root.set("recordCount", "3")
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            elif info.filename == "xl/pivotTables/pivotTable1.xml":
                root = etree.fromstring(data)
                etree.SubElement(root, f"{{{MAIN}}}location", ref="Q1:Q1")
                data = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
            target.writestr(info, data)


def _bind_oracle(output, operation, tmp_path) -> None:
    with zipfile.ZipFile(output) as package:
        matrix_sha256, rows, columns = _matrix_hash(package, "xl/worksheets/sheet1.xml", "Q1:Q1")
    oracle = {"schema_version": "1.0", "reports": [{"sheet": "Data", "name": "Pivot1", "range": "Q1:Q1", "rows": rows, "columns": columns, "matrix_sha256": matrix_sha256}]}
    oracle_path = tmp_path / "oracle.json"
    oracle_path.write_text(json.dumps(oracle), encoding="utf-8")
    operation["dependent_pivots"].update(oracle_path=str(oracle_path), oracle_sha256=sha256_path(oracle_path))


def _arrange(tmp_path, **native_options):
    seed = tmp_path / "seed.xlsx"
    intermediate = tmp_path / "intermediate.xlsx"
    output = tmp_path / "output.xlsx"
    _seed_package(seed)
    operation, schema = _operation_and_sidecar(tmp_path)
    preflight = preflight_package(seed, operation, schema)
    rewrite_intermediate_package(seed, intermediate, operation, schema, preflight)
    _simulate_native_excel(intermediate, output, **native_options)
    _bind_oracle(output, operation, tmp_path)
    return seed, output, operation, schema, preflight


def test_final_proof_accepts_translated_shared_calculated_column(tmp_path) -> None:
    seed, output, operation, schema, preflight = _arrange(tmp_path)
    proof = verify_final_package(seed, output, operation, schema, preflight, sha256_path(seed))
    assert proof["table_ref"] == "B3:D6"
    assert proof["body"]["formula_cells"] == 3
    assert proof["pivot_oracle"]["reports"][0]["sha256"]


def test_final_proof_accepts_topology_only_pivot_validation(tmp_path) -> None:
    seed, output, operation, schema, preflight = _arrange(tmp_path)
    operation["dependent_pivots"].pop("oracle_path")
    operation["dependent_pivots"].pop("oracle_sha256")

    proof = verify_final_package(seed, output, operation, schema, preflight, sha256_path(seed))

    assert proof["pivot_oracle"]["mode"] == "topology_only"
    assert proof["pivot_oracle"]["caches"] == [
        {"part": "xl/pivotCache/pivotCacheDefinition1.xml", "record_count": 3}
    ]
    assert proof["pivot_oracle"]["reports"][0]["location"] == "Q1:Q1"


def test_final_proof_rejects_horizontal_table_move(tmp_path) -> None:
    seed, output, operation, schema, preflight = _arrange(tmp_path, move_table=True)
    with pytest.raises(ContractError, match="geometry"):
        verify_final_package(seed, output, operation, schema, preflight, sha256_path(seed))


def test_final_proof_rejects_calculated_column_exception(tmp_path) -> None:
    seed, output, operation, schema, preflight = _arrange(tmp_path, formula_exception=True)
    with pytest.raises(ContractError, match="formula exception"):
        verify_final_package(seed, output, operation, schema, preflight, sha256_path(seed))
