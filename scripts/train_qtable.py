"""Offline Q-Table self-play driver → ``assets/learning_curve.png`` (E9/E11).

A Q-learning **COP** learns to capture a **fixed heuristic THIEF** on a small
grid, training over ``config.qlearning.episodes`` episodes with the hyper-params
from ``config.yaml`` (learning_rate/discount_factor/epsilon/episodes; Rule 4).
This is pure reinforcement learning on the game state-machine — **NO Gemini, no
MCP, no network** — exactly the optional RL extension the spec allows.

State = ``(cop_cell, thief_cell)`` (full observability, since this is the *offline
learner* that only produces the curve, not the live partial-observability run).
Action = a legal cop move name. The reward is dense-shaped so the curve is legible:
``+10`` on capture, ``-1`` per non-capturing step (move cost). The per-episode
total reward is logged and rises as the cop learns to corner the heuristic thief.
The Bellman update + epsilon-greedy live in :class:`strategy.qtable.QTable`; the
plot is rendered headless (Agg) by :func:`strategy.plots.plot_learning_curve`.

Run: ``uv run python scripts/train_qtable.py``  (writes ``assets/learning_curve.png``).
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cosmos77_ex06.game.board import Board  # noqa: E402
from cosmos77_ex06.game.moves import apply_move, legal_moves  # noqa: E402
from cosmos77_ex06.game.state import Cell  # noqa: E402
from cosmos77_ex06.shared.config import Config  # noqa: E402
from cosmos77_ex06.strategy import heuristic  # noqa: E402
from cosmos77_ex06.strategy.plots import plot_learning_curve  # noqa: E402
from cosmos77_ex06.strategy.qtable import QTable  # noqa: E402

GRID = [4, 4]  # small training grid (curve only); the live game uses config grid
MAX_STEPS = 30  # per-episode horizon for the offline learner
CAPTURE_REWARD = 10.0
STEP_COST = -1.0


def _thief_move(thief: Cell, cop: Cell, board: Board) -> Cell:
    """Move the fixed heuristic thief one step away from the cop (the target)."""
    action = heuristic.suggest_thief_action(cop, thief, board, _CFG)
    return apply_move(thief, action["direction"], board)


def run_episode(qt: QTable, board: Board, rng: random.Random) -> float:
    """Play one COP-learns-to-capture episode; return its total reward.

    The cop acts epsilon-greedily from ``QTable``; the thief is the deterministic
    heuristic evader; the Bellman update is applied after every cop step. Returns
    the episode's cumulative reward (rises as the policy improves).
    """
    cells = board.cells
    cop, thief = rng.choice(cells), rng.choice(cells)
    while thief == cop:
        thief = rng.choice(cells)
    total = 0.0
    for _ in range(MAX_STEPS):
        thief = _thief_move(thief, cop, board)  # thief moves first (turn_order)
        if cop == thief:
            break
        state = (cop, thief)
        actions = legal_moves(cop, board)
        direction = qt.select_action(state, actions)
        new_cop = apply_move(cop, direction, board)
        done = new_cop == thief
        reward = CAPTURE_REWARD if done else STEP_COST
        total += reward
        next_state = (new_cop, thief)
        qt.update(state, direction, reward, next_state, legal_moves(new_cop, board), done)
        cop = new_cop
        if done:
            break
    return total


def train(config: Config, seed: int = 7) -> QTable:
    """Train the Q-Table over ``config.qlearning.episodes`` self-play episodes."""
    rng = random.Random(seed)
    board = Board(GRID, allow_diagonal=bool(config.get("allow_diagonal")))
    qt = QTable(config, rng=rng)
    for _ in range(qt.episodes):
        qt.log_episode(run_episode(qt, board, rng))
    return qt


_CFG = Config()


def main() -> int:
    """Train the learner and render the learning curve to ``assets/``."""
    qt = train(_CFG)
    out = _CFG.repo_assets() / "learning_curve.png"
    path = plot_learning_curve(qt.episode_rewards, out)
    print(f"trained {qt.episodes} episodes; wrote {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
