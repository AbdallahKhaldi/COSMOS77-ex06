"""Tests for the version constant + config-version validation (CLAUDE.md rule 10)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.shared.version import VERSION, validate_config_version


def test_version_is_one_point_zero_zero() -> None:
    assert VERSION == "1.00"


def test_validate_accepts_matching_version() -> None:
    validate_config_version("1.00")  # must not raise


def test_validate_rejects_mismatch() -> None:
    with pytest.raises(ValueError, match="does not match project version"):
        validate_config_version("1.01")
