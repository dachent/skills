from __future__ import annotations

import csv
import json
import zipfile

from lxml import etree

from control_plane.ooxml_table_transaction import MAIN, preflight_package, rewrite_intermediate_package
from control_plane.table_sidecar import inspect_sidecar, load_sidecar_schema
from test_capabilities import _production_append


def _package(path, *, collision: bool = False) -> None:
    parts = {
        "[Content_Types].xml": """<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"/>""",
        "xl/workbook.xml": """<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Data" sheetId="1" r:id="rSheet"/></sheets><pivotCaches><pivotCache cacheId="1" r:id="rCache"/></pivotCaches></workbook>""",
        "xl/_rels/workbook.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rSheet" Target="worksheets/sheet1.xml"/><Relationship Id="rCache" Target="pivotCache/pivotCacheDefinition1.xml"/></Relationships>""",
        "xl/worksheets/_rels/sheet1.xml.rels": """<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rTable" Target="../tables/table1.xml"/></Relationships>""",
        "xl/tables/table1.xml": """<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" id="1" name="Data" displayName="Data" ref="B3:P195936" totalsRowShown="0"><autoFilter ref="B3:P195936"/><sortState ref="B4:P195936"><sortCondition ref="B4:B195936" descending="1"/></sortState><tableColumns count="15">%s</tableColumns></table>""" % "".join(
            f'<tableColumn id="{i}" name="{name}">{"<calculatedColumnFormula>1</calculatedColumnFormula>" if name.startswith("Calculated") else ""}</tableColumn>'
            for i, name in enumerate(["FileName", "CalculatedA", *[f"Value{i}" for i in range(2, 14)], "CalculatedB"], start=1)
        ),
        "xl/pivotCache/pivotCacheDefinition1.xml": """<pivotCacheDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><cacheSource type="worksheet"><worksheetSource name="Data"/></cacheSource></pivotCacheDefinition>""",
        "xl/pivotTables/pivotTable1.xml": """<pivotTableDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" cacheId="1"/>""",
        "xl/pivotTables/pivotTable2.xml": """<pivotTableDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" cacheId="1"/>""",
        "xl/pivotTables/pivotTable3.xml": """<pivotTableDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" cacheId="1"/>""",
        "xl/styles.xml": "<styleSheet xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\"/>",
    }
    cells = "".join(f'<c r="{chr(66+i)}4" s="1"><v>{i}</v></c>' for i in range(15))
    if collision:
        cells += '<c r="B195937"><v>collision</v></c>'
    parts["xl/worksheets/sheet1.xml"] = f"""<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><dimension ref="B3:P195936"/><sheetData><row r="3"/><row r="4">{cells}</row></sheetData><tableParts count="1"><tablePart r:id="rTable"/></tableParts></worksheet>"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as package:
        for name, data in parts.items():
            package.writestr(name, data)


def _sidecar(tmp_path):
    manifest = _production_append()
    operation = manifest["steps"][0]
    operation["table"].update(existing_body_rows=195933, final_body_rows=195935)
    operation["source"].update(row_count=2)
    names = [column["name"] for column in operation["table"]["columns"]]
    schema = {
        "schema_version": "1.0", "encoding": "utf-8", "delimiter": ",", "quotechar": '"', "has_header": True, "date_system": "1900",
        "columns": [
            {"id": i, "name": column["name"], "role": column["role"], "logical_type": column["logical_type"], "storage_type": ("number" if column["logical_type"] in {"number", "datetime"} else "inline_string"), "number_format": ("m/d/yyyy" if column["logical_type"] == "datetime" else None)}
            for i, column in enumerate(operation["table"]["columns"], start=1)
        ],
    }
    schema_path = tmp_path / "rows.schema.json"
    csv_path = tmp_path / "rows.csv"
    schema_path.write_text(json.dumps(schema), encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(names)
        for row in range(2):
            writer.writerow([f"=safe{row}" if column["role"] == "writable" else "" for column in operation["table"]["columns"]])
    stats = inspect_sidecar(csv_path, schema_path, scratch_dir=tmp_path)
    operation["source"].update(stats.to_dict(), path=str(csv_path), schema_path=str(schema_path))
    return operation, load_sidecar_schema(schema_path)


def test_streaming_rewrite_changes_only_target_sheet_and_emits_no_formula(tmp_path) -> None:
    workbook = tmp_path / "seed.xlsx"
    output = tmp_path / "intermediate.xlsx"
    _package(workbook)
    operation, schema = _sidecar(tmp_path)
    preflight = preflight_package(workbook, operation, schema)
    manifest = rewrite_intermediate_package(workbook, output, operation, schema, preflight)
    assert manifest["changed_parts"] == ["xl/tables/table1.xml", "xl/worksheets/sheet1.xml"]
    with zipfile.ZipFile(output) as package:
        sheet = etree.fromstring(package.read("xl/worksheets/sheet1.xml"))
        first = sheet.find(f".//{{{MAIN}}}c[@r='B195937']")
        assert first is not None
        assert first.get("t") == "inlineStr"
        assert first.find(f"{{{MAIN}}}f") is None
        assert first.findtext(f"{{{MAIN}}}is/{{{MAIN}}}t") == "=safe0"
        table = etree.fromstring(package.read("xl/tables/table1.xml"))
        assert table.get("ref") == "B3:P195938"
        assert table.find(f"{{{MAIN}}}autoFilter").get("ref") == "B3:P195938"
        sort_state = table.find(f"{{{MAIN}}}sortState")
        assert sort_state is not None
        assert sort_state.get("ref") == "B4:P195938"
        assert sort_state.find(f"{{{MAIN}}}sortCondition").get("ref") == "B4:B195938"


def test_growth_collision_rejects_before_rewrite(tmp_path) -> None:
    workbook = tmp_path / "seed.xlsx"
    _package(workbook, collision=True)
    operation, schema = _sidecar(tmp_path)
    try:
        preflight_package(workbook, operation, schema)
    except Exception as exc:
        assert getattr(exc, "code", None) == "PACKAGE_PREFLIGHT_INVALID"
    else:
        raise AssertionError("collision was admitted")
