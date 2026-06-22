"""Q-Table tests: hand-computed Bellman update + epsilon-greedy explore/exploit (E9)."""

from __future__ import annotations

import random

import pytest

from cosmos77_ex06.strategy.qtable import QTable


def test_bellman_update_matches_hand_computed_value(make_config) -> None:
    """Hand-computed example (asserts the EXACT resulting Q-value).

    alpha=0.5, gamma=0.9, q[s,a]=2.0, reward=1.0, max_a' q[s',a']=5.0, not done.
        q' = 2.0 + 0.5*(1.0 + 0.9*5.0 - 2.0)
           = 2.0 + 0.5*(1.0 + 4.5 - 2.0) = 2.0 + 0.5*3.5 = 2.0 + 1.75 = 3.75
    """
    config = make_config(
        qlearning={"learning_rate": 0.5, "discount_factor": 0.9, "epsilon": 0.0, "episodes": 10}
    )
    qt = QTable(config)
    qt.q[("s", "a")] = 2.0
    qt.q[("s2", "x")] = 5.0  # max_a' q[s', a'] = 5.0
    qt.q[("s2", "y")] = 4.0
    result = qt.update("s", "a", reward=1.0, next_state="s2", next_actions=["x", "y"], done=False)
    assert result == pytest.approx(3.75)
    assert qt.get("s", "a") == pytest.approx(3.75)


def test_bellman_update_drops_bootstrap_when_done(make_config) -> None:
    """Terminal transition: best_next_q == 0.

    q' = 2.0 + 0.5*(1.0 + 0.9*0 - 2.0) = 2.0 + 0.5*(-1.0) = 1.5
    """
    config = make_config(
        qlearning={"learning_rate": 0.5, "discount_factor": 0.9, "epsilon": 0.0, "episodes": 10}
    )
    qt = QTable(config)
    qt.q[("s", "a")] = 2.0
    qt.q[("s2", "x")] = 5.0  # must be IGNORED because done=True
    result = qt.update("s", "a", reward=1.0, next_state="s2", next_actions=["x"], done=True)
    assert result == pytest.approx(1.5)


def test_unseen_pairs_default_to_zero(config) -> None:
    qt = QTable(config)
    assert qt.get("nowhere", "noop") == 0.0
    assert qt.best_value("nowhere", []) == 0.0
    assert qt.best_value("nowhere", ["a", "b"]) == 0.0


def test_epsilon_zero_always_exploits_argmax(make_config) -> None:
    config = make_config(
        qlearning={"learning_rate": 0.1, "discount_factor": 0.9, "epsilon": 0.0, "episodes": 5}
    )
    qt = QTable(config, rng=random.Random(0))
    qt.q[("s", "N")] = 1.0
    qt.q[("s", "S")] = 9.0  # the argmax
    qt.q[("s", "E")] = 2.0
    for _ in range(50):  # never explores → always the argmax
        assert qt.select_action("s", ["N", "S", "E"]) == "S"


def test_epsilon_one_always_explores(make_config) -> None:
    config = make_config(
        qlearning={"learning_rate": 0.1, "discount_factor": 0.9, "epsilon": 1.0, "episodes": 5}
    )
    qt = QTable(config, rng=random.Random(42))
    qt.q[("s", "S")] = 9.0  # despite the clear argmax, exploration must reach others
    actions = ["N", "S", "E", "W"]
    chosen = {qt.select_action("s", actions) for _ in range(200)}
    assert chosen == set(actions)  # all explored (not pinned to the argmax)


def test_select_action_rejects_empty(config) -> None:
    qt = QTable(config)
    with pytest.raises(ValueError, match="no actions"):
        qt.select_action("s", [])


def test_episode_reward_logging(config) -> None:
    qt = QTable(config)
    qt.log_episode(3.0)
    qt.log_episode(-1.0)
    assert qt.episode_rewards == [3.0, -1.0]


def test_hyperparameters_read_from_config(config) -> None:
    qt = QTable(config)
    assert (qt.alpha, qt.gamma, qt.epsilon, qt.episodes) == (0.1, 0.9, 0.1, 200)
