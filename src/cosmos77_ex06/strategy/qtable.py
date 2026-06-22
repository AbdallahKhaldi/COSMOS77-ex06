"""Tabular Q-Learning: Bellman update + epsilon-greedy selection (E9, optional).

A minimal, fully-deterministic tabular learner whose only job is to evidence a
*learning curve* for the scientific README (E11); the §3 heuristic already
satisfies E9 (PRD_strategy §4). The Q-table is a plain ``dict[(state, action)]``.
The temporal-difference update is *exactly* the spec formula::

    q[s, a] <- q[s, a] + alpha * (reward + gamma * max_a' q[s', a'] - q[s, a])

with ``best_next_q == 0`` when the transition is terminal (``done``). Hyper-
parameters (alpha, gamma, epsilon, episodes) are read from ``config.qlearning``
(Rule 4 — nothing hardcoded). Per-episode total rewards are recorded for
:mod:`strategy.plots`. Training is offline self-play: no LLM, no MCP, no network.
"""

from __future__ import annotations

import random
from collections.abc import Hashable, Sequence

from cosmos77_ex06.shared.config import Config

State = Hashable
Action = Hashable


class QTable:
    """An epsilon-greedy tabular Q-learner with the standard Bellman update."""

    def __init__(self, config: Config, rng: random.Random | None = None) -> None:
        self.alpha = float(config.get("qlearning.learning_rate"))
        self.gamma = float(config.get("qlearning.discount_factor"))
        self.epsilon = float(config.get("qlearning.epsilon"))
        self.episodes = int(config.get("qlearning.episodes"))
        self._rng = rng if rng is not None else random.Random()
        self.q: dict[tuple[State, Action], float] = {}
        self.episode_rewards: list[float] = []

    def get(self, state: State, action: Action) -> float:
        """Return ``Q[state, action]`` (``0.0`` for an unseen pair)."""
        return self.q.get((state, action), 0.0)

    def best_value(self, state: State, actions: Sequence[Action]) -> float:
        """Return ``max_a' Q[state, a']`` over ``actions`` (``0.0`` if empty)."""
        if not actions:
            return 0.0
        return max(self.get(state, a) for a in actions)

    def select_action(self, state: State, actions: Sequence[Action]) -> Action:
        """Pick an action epsilon-greedily.

        With probability ``epsilon`` a uniformly-random legal action is explored;
        otherwise the greedy ``argmax_a Q[state, a]`` is exploited. Ties on the
        argmax are broken by ``actions`` order, so a seeded RNG makes the choice
        reproducible (Rule 17): ``epsilon == 0`` always exploits, ``epsilon == 1``
        always explores.
        """
        if not actions:
            raise ValueError("no actions to select from")
        if self._rng.random() < self.epsilon:
            return self._rng.choice(list(actions))
        best = max(self.get(state, a) for a in actions)
        for action in actions:  # first argmax in order → deterministic exploit
            if self.get(state, action) == best:
                return action
        return actions[0]  # pragma: no cover - unreachable; best is always present

    def update(
        self,
        state: State,
        action: Action,
        reward: float,
        next_state: State,
        next_actions: Sequence[Action],
        done: bool,
    ) -> float:
        """Apply the Bellman temporal-difference update and return the new ``Q[s, a]``.

        ``best_next_q`` is ``0`` when ``done`` (no bootstrapping past a terminal
        state), else ``max_a' Q[next_state, a']``. The new value is written back and
        returned so callers (and tests) can assert it directly.
        """
        best_next_q = 0.0 if done else self.best_value(next_state, next_actions)
        old = self.get(state, action)
        new = old + self.alpha * (reward + self.gamma * best_next_q - old)
        self.q[(state, action)] = new
        return new

    def log_episode(self, total_reward: float) -> None:
        """Record one training episode's total reward for the learning curve."""
        self.episode_rewards.append(float(total_reward))
