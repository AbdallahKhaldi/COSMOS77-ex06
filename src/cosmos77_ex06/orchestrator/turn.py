"""A single agent's turn: observe -> read -> reason -> speak -> act -> record (E4).

``play_turn`` is the heart of the per-turn loop (PRD §3). It is async because the
FastMCP ``Client`` is async. The LLM call lives in the orchestrator (``GeminiClient``,
E3); the MCP servers only execute the tools the engine routes to them. The
opponent's last NL message is relayed by the ENGINE (it holds the transcript), so
the two SEPARATE server processes need not share memory (E4, cloud-safe).
"""

from __future__ import annotations

from typing import Any

_MOVE_NAMES = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "STAY"}


async def _call_tool(client: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool through the FastMCP client and return its structured data."""
    result = await client.call_tool(name, args)
    data = getattr(result, "data", None)
    return data if isinstance(data, dict) else {"raw": data}


def _normalize_action(decision: dict[str, Any], role: str) -> tuple[str, dict[str, Any]]:
    """Map the LLM's proposed tool/args onto a legal game action (default STAY)."""
    tool = decision.get("tool")
    args = dict(decision.get("args") or {})
    if tool == "place_barrier" and role == "cop":
        return "place_barrier", {
            "role": role,
            "x": int(args.get("x", 0)),
            "y": int(args.get("y", 0)),
        }
    direction = str(args.get("direction", tool or "STAY")).upper()
    if direction not in _MOVE_NAMES:
        direction = "STAY"
    return "apply_move", {"role": role, "direction": direction}


async def play_turn(
    *,
    engine: Any,
    role: str,
    sub_game: int,
    opponent_message: str | None,
) -> dict[str, Any]:
    """Run one agent's turn; return ``{message, captured, board, entry}``."""
    client = engine.client_for(role)
    agent = engine.agent_for(role)
    observation = await _call_tool(client, "get_local_observation", {"role": role})
    estimate = agent.interpret(observation, opponent_message)
    prompt = agent.build_prompt(observation, opponent_message)
    decision = await engine.gemini.ask(role, prompt, client.session)
    message = decision.get("message") or f"({role} stays quiet)"
    coord_flagged = engine.guard.is_flagged(message)
    tool_name, tool_args = _normalize_action(decision, role)
    action_result = await _call_tool(client, tool_name, tool_args)
    captured = bool(action_result.get("captured", False))
    board = engine.board_snapshot()
    entry = engine.transcript.append(
        sub_game=sub_game,
        turn=engine.state.move_number,
        role=role,
        nl_message=message,
        tool=tool_name,
        args=tool_args,
        board=board,
        mcp_url=engine.url_for(role),
        coord_flagged=coord_flagged,
        estimate=estimate,
    )
    return {"message": message, "captured": captured, "board": board, "entry": entry}
