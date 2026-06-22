"""Render the cumulative cop-vs-thief score bar chart → ``assets/results_totals.png``.

Headless (Agg) matplotlib bar chart of the representative cumulative totals from
live Gemini cop-win sub-games on the 2x2/3x3 sanity rungs: per cop-win sub-game
the cop banks ``cop_win`` (20) and the thief takes ``thief_loss`` (5). Across the
representative captured sub-games the cumulative totals are **cop 20 / thief 5**.
The figure is embedded in the scientific README's Results section (E11). Pure
plotting — NO Gemini, no MCP, no network.

Run: ``uv run python scripts/generate_results_chart.py``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cosmos77_ex06.shared.config import Config  # noqa: E402

COP_TOTAL = 20  # representative cumulative cop score (cop_win banked on capture)
THIEF_TOTAL = 5  # representative cumulative thief score (thief_loss on capture)


def plot_results(out_path: str | Path) -> Path:
    """Plot the cop-vs-thief cumulative-totals bar chart and save a PNG."""
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    labels = ["Cop", "Thief"]
    totals = [COP_TOTAL, THIEF_TOTAL]
    colors = ["#3c82f0", "#e64646"]

    fig, ax = plt.subplots(figsize=(7, 5))
    bars = ax.bar(labels, totals, color=colors, width=0.55)
    for bar, value in zip(bars, totals, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.4,
            str(value),
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
        )
    ax.set_ylabel("cumulative score")
    ax.set_ylim(0, max(totals) + 4)
    ax.set_title(
        "Cumulative score — representative live Gemini cop-win sub-games\n(cop_win 20 / thief_loss 5 per capture)"
    )
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return out


def main() -> int:
    """Render the results bar chart to ``assets/results_totals.png``."""
    out = Config().repo_assets() / "results_totals.png"
    path = plot_results(out)
    print(f"wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
