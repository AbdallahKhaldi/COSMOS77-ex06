"""Render the Q-Table learning curve to ``assets/learning_curve.png`` (E11).

Headless-safe: matplotlib's non-interactive ``Agg`` backend is forced *before* the
library is imported (and matplotlib itself is lazy-imported inside the function), so
the plot is produced with no display — safe in CI and on a headless box. The figure
plots per-episode total reward plus a moving average; it is embedded in the
scientific README as evidence the tabular learner converges (PRD_strategy §4.3).
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from pathlib import Path


def _moving_average(values: Sequence[float], window: int) -> list[float]:
    """Return a trailing simple moving average (window shrinks at the start)."""
    out: list[float] = []
    for i in range(len(values)):
        lo = max(0, i - window + 1)
        chunk = values[lo : i + 1]
        out.append(sum(chunk) / len(chunk))
    return out


def plot_learning_curve(
    episode_rewards: Sequence[float],
    out_path: str | Path,
    window: int = 10,
) -> Path:
    """Plot per-episode reward + a moving average and save a PNG to ``out_path``.

    Forces the Agg backend and lazy-imports matplotlib so the call never needs a
    display. Returns the path written. Raises :class:`ValueError` if there are no
    rewards to plot.
    """
    if not episode_rewards:
        raise ValueError("no episode rewards to plot")
    os.environ.setdefault("MPLBACKEND", "Agg")
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    episodes = range(1, len(episode_rewards) + 1)
    avg = _moving_average(episode_rewards, window)

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(episodes, episode_rewards, color="#9bbcff", linewidth=1, label="episode reward")
    ax.plot(episodes, avg, color="#1f4e9c", linewidth=2, label=f"moving avg (w={window})")
    ax.set_xlabel("episode")
    ax.set_ylabel("total reward")
    ax.set_title("Q-Table learning curve (Cops & Robbers self-play)")
    ax.legend(loc="best")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out, dpi=120)  # pragma: no cover - I/O side effect
    plt.close(fig)
    return out
