"""Partial-observability belief inference for the agents (E4/E11).

:class:`BeliefMixin` turns a role's bounded local observation plus the opponent's
last free natural-language message into a private *estimate* of the opponent under
partial observability. It is split out of :mod:`agents.base` (Rule 1 / Rule 3) and
mixed into :class:`~cosmos77_ex06.agents.base.BaseAgent`, so callers still invoke
``agent.interpret(...)`` unchanged. Holds no LLM and no I/O (E3).
"""

from __future__ import annotations

from typing import Any


class BeliefMixin:
    """Belief-formation helpers expecting a ``role`` attribute on the host class."""

    role: str

    def interpret(
        self, observation: dict[str, Any], opponent_message: str | None
    ) -> dict[str, Any]:
        """Form a private belief about the opponent under partial observability (E4/E11).

        Returns a structured estimate recorded per turn as graded evidence:
        ``seen`` (opponent inside the vision window), ``opponent_cell`` (confirmed
        cell, else ``None``), ``heard`` (the last claim), and ``credibility`` —
        ``confirmed`` when the local view corroborates/contradicts a claim (bluff
        DISCOUNTED), ``inferred`` on words alone, ``none`` when silent. The estimate
        changes when the incoming message changes (PRD §10 belief/deception tests).
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
        ``visible_cells`` (E4); outside the window there is no such field, so the
        belief must be inferred from words alone.
        """
        opp_role = "thief" if self.role == "cop" else "cop"
        for cell in observation.get("visible_cells", []):
            if cell.get("occupant") == opp_role:
                return [int(cell["x"]), int(cell["y"])]
        return None
