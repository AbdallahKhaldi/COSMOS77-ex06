"""Tests for the pre-send byte-for-byte diff-check (E12, §8): identical vs mismatch."""

from __future__ import annotations

from pathlib import Path

from cosmos77_ex06.bonus.diff_check import (
    compare_bytes,
    diff_files,
    format_result,
    key_diff,
)


def test_identical_bytes_report_identical() -> None:
    result = compare_bytes(b'{"a":1}', b'{"a":1}')
    assert result == {"identical": True, "n_bytes": 7, "first_diff": None}
    assert "IDENTICAL" in format_result(result)


def test_mismatch_reports_first_diff_offset() -> None:
    result = compare_bytes(b'{"a":1}', b'{"a":2}')
    assert result["identical"] is False
    assert result["first_diff"] == 5
    assert "MISMATCH at byte 5" in format_result(result)


def test_mismatch_on_length_only() -> None:
    result = compare_bytes(b'{"a":1}', b'{"a":1} ')
    assert result["identical"] is False
    assert result["first_diff"] == 7


def test_key_diff_localizes_changed_field() -> None:
    diff = key_diff('{"x":1,"y":2}', '{"x":1,"y":3}')
    assert diff == {"y": {"left": 2, "right": 3}}


def test_key_diff_on_invalid_json_returns_empty() -> None:
    assert key_diff("not json", "{}") == {}


def test_diff_files_identical_and_mismatch(tmp_path: Path) -> None:
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    a.write_text('{"k":1}', encoding="utf-8")
    b.write_text('{"k":1}', encoding="utf-8")
    assert diff_files(a, b)["identical"] is True

    b.write_text('{"k":2}', encoding="utf-8")
    result = diff_files(a, b)
    assert result["identical"] is False
    assert result["key_diff"] == {"k": {"left": 1, "right": 2}}
    assert "field 'k'" in format_result(result)
