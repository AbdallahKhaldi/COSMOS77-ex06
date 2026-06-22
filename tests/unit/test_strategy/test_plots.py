"""Learning-curve plotting smoke tests (headless Agg; figure is produced)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cosmos77_ex06.strategy.plots import _moving_average, plot_learning_curve


def test_moving_average_trailing_window() -> None:
    assert _moving_average([1.0, 2.0, 3.0, 4.0], window=2) == [1.0, 1.5, 2.5, 3.5]
    assert _moving_average([5.0], window=10) == [5.0]


def test_plot_learning_curve_writes_png(tmp_path: Path) -> None:
    rewards = [float(i % 5) for i in range(40)]
    out = tmp_path / "sub" / "learning_curve.png"
    result = plot_learning_curve(rewards, out, window=5)
    assert result == out
    assert out.exists() and out.stat().st_size > 0


def test_plot_learning_curve_uses_agg_backend(tmp_path: Path) -> None:
    plot_learning_curve([1.0, 2.0, 3.0], tmp_path / "curve.png")
    import matplotlib

    assert matplotlib.get_backend().lower() == "agg"  # headless-safe


def test_plot_learning_curve_rejects_empty(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no episode rewards"):
        plot_learning_curve([], tmp_path / "x.png")
