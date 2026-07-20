from __future__ import annotations

from control_plane.ooxml_verifier import _numbers_equivalent


def test_excel_binary_float_roundtrip_matches_source_decimal_scale() -> None:
    assert _numbers_equivalent("153.89", "153.88999999999999")
    assert _numbers_equivalent("37.3", "37.299999999999997")


def test_excel_binary_float_roundtrip_rejects_business_value_change() -> None:
    assert not _numbers_equivalent("153.89", "153.88")
    assert not _numbers_equivalent("123456789", "123456790")
