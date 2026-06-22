"""Smoke tests for the offline Q-Table training driver (E9/E11 learning curve).

Pure RL on the game state-machine — NO Gemini, no MCP, no network — so the driver
trains over a handful of episodes deterministically and produces a rising-ish
reward log that :mod:`strategy.plots` renders. We exercise a *single* episode and
a short training run on a seeded RNG and assert the curve log is populated.
"""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

from cosmos77_ex06.game.board import Board
from cosmos77_ex06.strategy.qtable import QTable

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "train_qtable.py"


def _load_driver():
    spec = importlib.util.spec_from_file_location("train_qtable", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_episode_returns_a_finite_reward(config) -> None:
    driver = _load_driver()
    board = Board(driver.GRID, allow_diagonal=bool(config.get("allow_diagonal")))
    qt = QTable(config, rng=random.Random(7))
    reward = driver.run_episode(qt, board, random.Random(3))
    assert isinstance(reward, float)
    # A non-capturing step costs STEP_COST and capture pays CAPTURE_REWARD.
    assert driver.STEP_COST * driver.MAX_STEPS <= reward <= driver.CAPTURE_REWARD


def test_train_logs_one_reward_per_episode(config) -> None:
    driver = _load_driver()
    qt = driver.train(config, seed=11)
    assert len(qt.episode_rewards) == qt.episodes
    assert all(isinstance(r, float) for r in qt.episode_rewards)
    # Training must have populated the Q-table (the cop learned *something*).
    assert qt.q


def test_learning_trend_improves_early(make_config) -> None:
    """The trailing-window mean late in training beats the first window (it learns)."""
    driver = _load_driver()
    config = make_config(
        qlearning={
            "learning_rate": 0.2,
            "discount_factor": 0.9,
            "epsilon": 0.1,
            "episodes": 120,
        }
    )
    qt = driver.train(config, seed=5)
    rewards = qt.episode_rewards
    first = sum(rewards[:20]) / 20
    last = sum(rewards[-20:]) / 20
    assert last > first  # the moving-average rises across training
