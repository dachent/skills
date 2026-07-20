from __future__ import annotations

from lxml import etree

from control_plane.ooxml_table_transaction import MAIN
from control_plane.ooxml_verifier import _cell_record


def test_cell_record_accepts_formula_cached_string() -> None:
    cell = etree.fromstring(
        f'<c xmlns="{MAIN}" r="O4" t="str"><f>YEAR(B4)&amp;"-03"</f><v>2026-03</v></c>'
    )

    record = _cell_record(cell, [], {}, "O4")

    assert record == {
        "storage": "inline_string",
        "value": "2026-03",
        "formula": 'YEAR(B4)&"-03"',
        "style": None,
    }
