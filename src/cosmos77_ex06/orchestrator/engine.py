"""The GameEngine — MCP Client + game engine in one (E3, E4, E5).

Owns the cop + thief FastMCP ``Client`` sessions (token auth), the authoritative
:class:`GameState`, the agents, the :class:`GeminiClient`, and the turn loop
(thief -> cop, capture/limit checks) over ``num_games`` sub-games, recording the
full transcript. The LLM call lives HERE; the servers only execute tools. The
engine is the E4 message RELAY (the transcript feeds the opponent's last NL line
into the active prompt), so the NL channel is process-independent. An optional
``on_turn`` hook feeds the live GUI (E10); turn execution is split into ``turn.py``."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cosmos77_ex06.agents.base import make_agent
from cosmos77_ex06.game import rules
from cosmos77_ex06.game.state import GameState, SubGameResult
from cosmos77_ex06.orchestrator.gemini_client import GeminiClient
from cosmos77_ex06.orchestrator.guard import CoordinateGuard
from cosmos77_ex06.orchestrator.transcript import Transcript
from cosmos77_ex06.orchestrator.turn import play_turn
from cosmos77_ex06.shared.config import Config


class GameEngine:
    """Drives the per-turn loop and the multi-sub-game rhythm over MCP."""

    def __init__(
        self,
        config: Config,
        clients: dict[str, Any],
        gemini: GeminiClient,
        urls: dict[str, str] | None = None,
        state: GameState | None = None,
        on_turn: Callable[[GameState], None] | None = None,
    ) -> None:
        self.config, self.clients, self.gemini, self.on_turn = config, clients, gemini, on_turn
        self.urls = urls or {r: str(config.get(f"mcp.{r}_url")) for r in ("cop", "thief")}
        self.turn_order = list(config.get("turn_order"))
        self.num_games = int(config.get("num_games"))
        self.max_moves = int(config.get("max_moves"))
        self.agents = {r: make_agent(r, config) for r in ("cop", "thief")}
        self.guard = CoordinateGuard(config)
        self.transcript = Transcript()
        self.state: GameState = state if state is not None else self._fresh_state()

    def _fresh_state(self) -> GameState:
        """Build a fresh sub-game state (opposite corners, thief first)."""
        grid = list(self.config.get("grid_size"))
        return GameState(
            grid_size=grid,
            cop_pos=(grid[0] - 1, grid[1] - 1),
            thief_pos=(0, 0),
            max_moves=self.max_moves,
            allow_diagonal=bool(self.config.get("allow_diagonal")),
            turn_order=self.turn_order,
            current_role=self.turn_order[0],
        )

    def _reset_state_in_place(self) -> None:
        """Reset the SHARED state object for a new sub-game (servers keep their handle)."""
        fresh = self._fresh_state()
        for field, value in vars(fresh).items():
            setattr(self.state, field, value)

    def client_for(self, role: str) -> Any:
        """The FastMCP client bound to ``role``'s server."""
        return self.clients[role]

    def agent_for(self, role: str) -> Any:
        """The prompt-building agent for ``role``."""
        return self.agents[role]

    def url_for(self, role: str) -> str:
        """The MCP server URL ``role``'s calls hit (transcript evidence)."""
        return self.urls[role]

    def board_snapshot(self) -> dict[str, Any]:
        """A minimal board snapshot for the transcript."""
        s = self.state
        return {
            "cop": list(s.cop_pos),
            "thief": list(s.thief_pos),
            "barriers": [list(b) for b in sorted(s.barriers)],
            "move": s.move_number,
        }

    async def play_sub_game(self, index: int) -> SubGameResult:
        """Run one sub-game (thief -> cop each move) until capture or the limit."""
        self._reset_state_in_place()
        while self.state.move_number < self.max_moves:
            captured = await self._play_full_move(index)
            if captured:
                break
        return self._result()

    async def _play_full_move(self, index: int) -> bool:
        """Play one full move (each role once); return True on capture.

        A barrier action does not move an agent, so the engine guarantees forward
        progress after each full move so the loop always terminates at max_moves.
        """
        start = self.state.move_number
        for role in self.turn_order:
            outcome = await play_turn(
                engine=self,
                role=role,
                sub_game=index,
                opponent_message=self.transcript.last_from_opponent(role),
            )
            if self.on_turn is not None:
                self.on_turn(self.state)
            if outcome["captured"]:
                return True
        if self.state.move_number == start:
            self.state.move_number += 1
            self.state.current_role = self.turn_order[0]
        return False

    def _result(self) -> SubGameResult:
        """Score the finished sub-game from the config table."""
        outcome = rules.subgame_result(self.state)
        scores = rules.score_for(outcome, self.config)
        winner = "cop" if outcome == rules.COP_WIN else "thief"
        self.state.scores = scores
        return SubGameResult(
            winner=winner,
            scores=scores,
            move_count=self.state.move_number,
            state=self.state,
            log=self.transcript.to_list(),
        )

    async def play_game(self) -> dict[str, Any]:
        """Run ``num_games`` sub-games and return the transcript + accumulated totals."""
        totals = {"cop": 0, "thief": 0}
        sub_games: list[dict[str, Any]] = []
        for i in range(1, self.num_games + 1):
            r = await self.play_sub_game(i)
            totals = {k: totals[k] + r.scores[k] for k in totals}
            sub_games.append(
                {"index": i, "winner": r.winner, "scores": r.scores, "moves": r.move_count}
            )
        return {
            "sub_games": sub_games,
            "totals": totals,
            "transcript": self.transcript.to_list(),
            "messages": self.transcript.messages(),
        }
