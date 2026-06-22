"""Agent prompt-builder + decision-parser tests (E4)."""

from __future__ import annotations

import pytest

from cosmos77_ex06.agents.base import CopAgent, ThiefAgent, make_agent
from cosmos77_ex06.shared.config import Config


def test_make_agent_returns_role_subclasses(orch_config: Config) -> None:
    assert isinstance(make_agent("cop", orch_config), CopAgent)
    assert isinstance(make_agent("thief", orch_config), ThiefAgent)


def test_make_agent_rejects_unknown_role(orch_config: Config) -> None:
    with pytest.raises(ValueError, match="unknown role"):
        make_agent("warden", orch_config)


def test_cop_prompt_offers_barrier_thief_does_not(orch_config: Config) -> None:
    obs = {"self": [1, 1]}
    cop_prompt = make_agent("cop", orch_config).build_prompt(obs, None)
    thief_prompt = make_agent("thief", orch_config).build_prompt(obs, "all quiet here")
    assert "place_barrier" in cop_prompt
    assert "place_barrier" not in thief_prompt


def test_prompt_forbids_coordinates_and_relays_message(orch_config: Config) -> None:
    prompt = make_agent("thief", orch_config).build_prompt({"self": [0, 0]}, "I'm by the west wall")
    assert "NEVER raw coordinates" in prompt
    assert "I'm by the west wall" in prompt  # opponent message relayed into the prompt
    assert "no message from the opponent yet" not in prompt


def test_prompt_handles_missing_opponent_message(orch_config: Config) -> None:
    prompt = make_agent("cop", orch_config).build_prompt({"self": [1, 1]}, None)
    assert "no message from the opponent yet" in prompt


def test_parse_decision_normalizes(orch_config: Config) -> None:
    decision = make_agent("cop", orch_config).parse_decision(
        "  closing in  ", "apply_move", {"direction": "NW"}
    )
    assert decision == {
        "role": "cop",
        "message": "closing in",
        "tool": "apply_move",
        "args": {"direction": "NW"},
    }
