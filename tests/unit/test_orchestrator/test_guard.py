"""Coordinate-leak guard tests (E4, PRD §7.5/§10)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.orchestrator.guard import CoordinateGuard
from cosmos77_ex06.shared.config import Config


@pytest.mark.parametrize(
    "leak",
    [
        "I'm at (3,4) waiting.",
        "Move to row 3 now.",
        "Hold col 4.",
        "Target [3, 4].",
        "Meet me 3, 4.",
    ],
)
def test_guard_flags_coordinate_shaped_messages(orch_config: Config, leak: str) -> None:
    guard = CoordinateGuard(orch_config)
    assert guard.is_flagged(leak), f"guard missed coordinate leak: {leak!r}"


@pytest.mark.parametrize(
    "prose",
    [
        "I'm hugging the western wall.",
        "Closing on the corner, nowhere to run.",
        "All quiet near the center.",
        "",
    ],
)
def test_guard_passes_clean_natural_language(orch_config: Config, prose: str) -> None:
    guard = CoordinateGuard(orch_config)
    assert not guard.is_flagged(prose)
