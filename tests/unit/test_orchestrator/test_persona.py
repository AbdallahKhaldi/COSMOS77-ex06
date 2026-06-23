"""The config-driven persona (E4 NL voice) is injected only when configured."""

from __future__ import annotations

from cosmos77_ex06.agents.base import make_agent
from cosmos77_ex06.shared.config import Config


def test_persona_off_by_default_keeps_prompt_clean(config: Config) -> None:
    """With no persona in config, the prompt carries no STYLE line (Phase-4 unchanged)."""
    prompt = make_agent("thief", config).build_prompt({"self": "(1,1)"}, None)
    assert "STYLE:" not in prompt


def test_persona_injected_per_role_when_configured(config: Config) -> None:
    """A configured persona becomes an in-character STYLE line in that role's prompt."""
    config._data["persona"] = {"thief": "be a roguish thief", "cop": "be a noir detective"}
    thief_prompt = make_agent("thief", config).build_prompt({"self": "(0,0)"}, "catch me")
    cop_prompt = make_agent("cop", config).build_prompt({"self": "(2,2)"}, "i'm cornered")
    assert "STYLE: be a roguish thief" in thief_prompt
    assert "STYLE: be a noir detective" in cop_prompt
    # personas never override the no-coordinates rule
    assert "NEVER raw" in thief_prompt
