"""Strategy-as-suggestion integration: the prompt HINT is optional + default-off (E9)."""

from __future__ import annotations

from cosmos77_ex06.agents.base import make_agent


def test_prompt_unchanged_when_no_suggestion(config) -> None:
    """Default (no suggestion) yields a prompt with no HINT line — Phase-4 unchanged."""
    agent = make_agent("cop", config)
    obs = {"self": [1, 1]}
    without = agent.build_prompt(obs, None)
    explicit_default = agent.build_prompt(obs, None, suggestion=None)
    assert "HINT" not in without
    assert without == explicit_default  # byte-identical to the Phase-4 prompt


def test_prompt_appends_hint_when_suggestion_given(config) -> None:
    agent = make_agent("cop", config)
    prompt = agent.build_prompt({"self": [1, 1]}, None, suggestion="NE")
    assert "HINT" in prompt
    assert "NE" in prompt
    assert "accept or override" in prompt


def test_strategy_disabled_by_default_in_config(config) -> None:
    assert bool(config.get("strategy.enabled", False)) is False
