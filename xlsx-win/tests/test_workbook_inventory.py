"""Workbook inventory tests: OOXML package inspection without trusting openpyxl.

Every risk-feature test builds a plain workbook with openpyxl, then injects
the *raw OOXML part* that indicates the feature directly into the zip
package with the standard library `zipfile` module, and asserts
`inspect_workbook` detects it. This deliberately never asks openpyxl's own
object model whether a feature is present -- that would be circular, since
part of this module's job is deciding whether openpyxl is even safe to open
the file with.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

import openpyxl
import pytest

from control_plane.workbook_inventory import inspect_workbook


def _make_plain_workbook(path: Path, sheet_names: tuple = ("Sheet1",)) -> None:
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for name in sheet_names:
        wb.create_sheet(name)
    wb.save(path)


def _copy_with_extra_entry(src: Path, dest: Path, entry_name: str, content: bytes = b"stub") -> None:
    dest.write_bytes(src.read_bytes())
    with zipfile.ZipFile(dest, "a") as zf:
        zf.writestr(entry_name, content)


def test_nonexistent_path_reports_exists_false_for_new_workbook_intent(tmp_path) -> None:
    inventory = inspect_workbook(tmp_path / "brand_new.xlsx")

    assert inventory.exists is False
    assert inventory.file_format == "xlsx"


def test_plain_xlsx_has_no_risk_features_and_is_classifiable(tmp_path) -> None:
    path = tmp_path / "plain.xlsx"
    _make_plain_workbook(path, ("Data", "Summary"))

    inventory = inspect_workbook(path)

    assert inventory.exists is True
    assert inventory.file_format == "xlsx"
    assert inventory.sheet_count == 2
    assert inventory.is_classifiable is True
    assert inventory.has_macros is False
    assert inventory.is_signed is False
    assert inventory.has_external_links is False
    assert inventory.has_data_model is False
    assert inventory.has_pivots is False
    assert inventory.has_slicers is False
    assert inventory.has_embedded_objects is False
    assert inventory.has_connections is False


def test_vba_project_part_sets_has_macros(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    macro_path = tmp_path / "macro.xlsm"
    _copy_with_extra_entry(plain, macro_path, "xl/vbaProject.bin")

    inventory = inspect_workbook(macro_path)

    assert inventory.file_format == "xlsm"
    assert inventory.has_macros is True
    assert inventory.is_signed is False


def test_signature_origin_part_sets_is_signed(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    signed_path = tmp_path / "signed.xlsx"
    _copy_with_extra_entry(plain, signed_path, "_xmlsignatures/origin.sigs")

    inventory = inspect_workbook(signed_path)

    assert inventory.is_signed is True
    assert inventory.has_macros is False


def test_external_link_part_sets_has_external_links(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    linked_path = tmp_path / "linked.xlsx"
    _copy_with_extra_entry(plain, linked_path, "xl/externalLinks/externalLink1.xml")

    inventory = inspect_workbook(linked_path)

    assert inventory.has_external_links is True


def test_data_model_part_sets_has_data_model(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    model_path = tmp_path / "model.xlsx"
    _copy_with_extra_entry(plain, model_path, "xl/model/item1.data")

    inventory = inspect_workbook(model_path)

    assert inventory.has_data_model is True


def test_pivot_cache_part_sets_has_pivots(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    pivot_path = tmp_path / "pivot.xlsx"
    _copy_with_extra_entry(plain, pivot_path, "xl/pivotCache/pivotCacheDefinition1.xml")

    inventory = inspect_workbook(pivot_path)

    assert inventory.has_pivots is True


def test_slicer_cache_part_sets_has_slicers(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    slicer_path = tmp_path / "slicer.xlsx"
    _copy_with_extra_entry(plain, slicer_path, "xl/slicerCaches/slicerCache1.xml")

    inventory = inspect_workbook(slicer_path)

    assert inventory.has_slicers is True


def test_embeddings_part_sets_has_embedded_objects(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    embed_path = tmp_path / "embed.xlsx"
    _copy_with_extra_entry(plain, embed_path, "xl/embeddings/oleObject1.bin")

    inventory = inspect_workbook(embed_path)

    assert inventory.has_embedded_objects is True


def test_connections_part_sets_has_connections(tmp_path) -> None:
    plain = tmp_path / "plain.xlsx"
    _make_plain_workbook(plain)
    connections_path = tmp_path / "connections.xlsx"
    _copy_with_extra_entry(plain, connections_path, "xl/connections.xml")

    inventory = inspect_workbook(connections_path)

    assert inventory.has_connections is True
    assert inventory.has_macros is False


def test_corrupted_xlsx_fails_closed_as_unclassifiable_instead_of_raising(tmp_path) -> None:
    path = tmp_path / "corrupt.xlsx"
    path.write_bytes(b"this is not a zip file at all")

    inventory = inspect_workbook(path)  # must not raise

    assert inventory.exists is True
    assert inventory.is_classifiable is False


def test_zip_without_content_types_part_fails_closed_as_unclassifiable(tmp_path) -> None:
    path = tmp_path / "not_ooxml.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("hello.txt", "this is a valid zip, but not an OOXML package")

    inventory = inspect_workbook(path)

    assert inventory.exists is True
    assert inventory.is_classifiable is False


def test_xls_is_a_shallow_format_and_is_still_classifiable(tmp_path) -> None:
    path = tmp_path / "legacy.xls"
    path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1stub-legacy-binary-xls")

    inventory = inspect_workbook(path)

    assert inventory.exists is True
    assert inventory.file_format == "xls"
    assert inventory.is_classifiable is True


def test_csv_is_a_shallow_format(tmp_path) -> None:
    path = tmp_path / "data.csv"
    path.write_text("a,b,c\n1,2,3\n", encoding="utf-8")

    inventory = inspect_workbook(path)

    assert inventory.exists is True
    assert inventory.file_format == "csv"


def test_tsv_is_a_shallow_format(tmp_path) -> None:
    path = tmp_path / "data.tsv"
    path.write_text("a\tb\tc\n1\t2\t3\n", encoding="utf-8")

    inventory = inspect_workbook(path)

    assert inventory.exists is True
    assert inventory.file_format == "tsv"


def test_inventory_is_deterministic_across_repeated_calls(tmp_path) -> None:
    path = tmp_path / "plain.xlsx"
    _make_plain_workbook(path, ("Data",))

    first = inspect_workbook(path)
    second = inspect_workbook(path)

    assert first == second
