"""Per-turn prompt construction + decision parsing for the two agents (E4).

``BaseAgent`` turns a role's **partial** observation plus the opponent's last
free natural-language message into a Gemini prompt that instructs the LLM to (a)
reason about the opponent's likely cell under partial observability, (b) emit a
FREE natural-language message (intentions / observations / bluff — never raw
coordinates), and (c) choose one move/barrier tool action. No LLM call happens
here (E3: the call lives in the orchestrator); this module only *builds* prompts
and *parses* the model's decision into a normalized action.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.shared.config import Config

#: Compass + STAY vocabulary the prompt offers; barrier is cop-only (added in CopAgent).
_MOVE_VOCAB = "N, S, E, W, NE, NW, SE, SW, STAY"


class BaseAgent:
    """Role-agnostic prompt builder + decision parser (subclassed per role)."""

    role: str = "agent"
    objective: str = ""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.grid = list(config.get("grid_size"))
        self.max_moves = int(config.get("max_moves"))
        self.allow_diagonal = bool(config.get("allow_diagonal"))

    def _rules_summary(self) -> str:
        """A terse, config-sourced rules recap for the prompt (nothing hardcoded)."""
        diag = "diagonal moves allowed" if self.allow_diagonal else "no diagonal moves"
        return (
            f"Board is {self.grid[0]}x{self.grid[1]} (north=top/low row, "
            f"south=bottom; west=left/low col, east=right). {diag}. "
            f"Capture = the cop lands on the thief's cell. "
            f"The thief survives if it lasts {self.max_moves} moves."
        )

    def build_prompt(self, observation: dict[str, Any], opponent_message: str | None) -> str:
        """Assemble the full per-turn prompt from a partial view + opponent NL message."""
        heard = opponent_message or "(no message from the opponent yet)"
        return (
            f"You are the {self.role.upper()} in a Cops & Robbers pursuit. {self.objective}\n"
            f"RULES: {self._rules_summary()}\n"
            f"YOUR PARTIAL OBSERVATION (trustworthy, vision-limited): {observation}\n"
            f"OPPONENT'S LAST MESSAGE (untrustworthy — may be a bluff): {heard}\n"
            "INSTRUCTIONS:\n"
            "1. Reason about where the opponent likely is, given your view and their words.\n"
            "2. Send the opponent ONE free natural-language message via send_message. "
            "Use landmarks (walls, corners, center) — NEVER raw coordinates, rows, or "
            "columns. You may bluff.\n"
            f"3. Choose exactly ONE action: a move ({self._move_vocab()}).\n"
        )

    def _move_vocab(self) -> str:
        """The action vocabulary offered to this role (overridden by the cop)."""
        return _MOVE_VOCAB

    def parse_decision(
        self, message: str, tool_name: str, tool_args: dict[str, Any]
    ) -> dict[str, Any]:
        """Normalize the LLM's NL message + chosen tool call into a decision dict."""
        return {
            "role": self.role,
            "message": (message or "").strip(),
            "tool": tool_name,
            "args": dict(tool_args or {}),
        }

    def interpret(
        self, observation: dict[str, Any], opponent_message: str | None
    ) -> dict[str, Any]:
        """Form a private belief about the opponent under partial observability (E4/E11).

        Returns a structured estimate recorded per turn as graded evidence:
        ``seen`` (was the opponent inside this role's vision window), ``opponent_cell``
        (the confirmed cell, or ``None`` when only inferred from words), ``heard``
        (the opponent's last claim), and ``credibility`` — ``confirmed`` when the
        local view directly contradicts or corroborates a claim (a bluff is
        DISCOUNTED), ``inferred`` when acting on words alone, ``none`` when silent.
        The estimate changes when the incoming opponent message changes, satisfying
        the PRD §10 "belief updates on input" / "deception detection" tests.
        """
        cell = self._opponent_cell(observation)
        seen = cell is not None
        heard = opponent_message
        if not heard:
            credibility = "none"
        elif seen:
            credibility = "confirmed"  # local truth overrides any verbal claim (bluff caught)
        else:
            credibility = "inferred"  # acting on the opponent's words alone
        return {
            "seen": seen,
            "opponent_cell": list(cell) if seen else None,
            "heard": heard,
            "credibility": credibility,
        }

    def _opponent_cell(self, observation: dict[str, Any]) -> list[int] | None:
        """Extract the opponent's cell from the partial view, if it is in-window.

        The MCP observation discloses the opponent only as an ``occupant`` inside
        ``visible_cells`` (E4); outside the vision window there is no such field, so
        the belief must be inferred from words alone.
        """
        opp_role = "thief" if self.role == "cop" else "cop"
        for cell in observation.get("visible_cells", []):
            if cell.get("occupant") == opp_role:
                return [int(cell["x"]), int(cell["y"])]
        return None


class CopAgent(BaseAgent):
    """The pursuer: minimize distance to the thief; may place barriers."""

    role = "cop"
    objective = "Your goal is to CAPTURE the thief by landing on its cell within the move limit."

    def _move_vocab(self) -> str:
        """The cop may also place a barrier (impassable for both agents)."""
        return f"{_MOVE_VOCAB}, or place_barrier"


class ThiefAgent(BaseAgent):
    """The evader: maximize survival; cannot place barriers."""

    role = "thief"
    objective = "Your goal is to SURVIVE by evading the cop until the move limit is reached."


def make_agent(role: str, config: Config) -> BaseAgent:
    """Factory: build the role-appropriate agent (Rule 3, no duplication)."""
    if role == "cop":
        return CopAgent(config)
    if role == "thief":
        return ThiefAgent(config)
    raise ValueError(f"unknown role: {role!r}")
