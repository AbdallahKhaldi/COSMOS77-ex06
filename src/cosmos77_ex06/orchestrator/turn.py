"""A single agent's turn: observe -> read -> reason -> speak -> act -> record (E4).

``play_turn`` is the heart of the per-turn loop (PRD §3). It is async because the
FastMCP ``Client`` is async. The LLM call lives in the orchestrator (``GeminiClient``,
E3); the MCP servers only execute the tools the engine routes to them. The
opponent's last NL message is relayed by the ENGINE (it holds the transcript), so
the two SEPARATE server processes need not share memory (E4, cloud-safe).
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.orchestrator import tactics, turn_log
from cosmos77_ex06.shared.logging_setup import get_logger

_MOVE_NAMES = {"N", "S", "E", "W", "NE", "NW", "SE", "SW", "STAY"}
_LOG = get_logger("cosmos77_ex06.orchestrator.turn")


def _emit_turn_log(engine: Any, entry: dict[str, Any]) -> None:
    """Emit the structured per-turn comms record (E10/E6); additive, no state change."""
    config = getattr(engine, "config", None)
    fmt = str(config.get("logging.format", default="human")) if config else "human"
    show_url = bool(config.get("logging.show_server_url", default=True)) if config else True
    record = turn_log.build_record(entry, show_server_url=show_url)
    _LOG.info(turn_log.format_record(record, fmt))


def _emit_event(engine: Any, entry: dict[str, Any], captured: bool) -> None:
    """Feed a structured per-turn event to the engine's optional live hook (web console).

    Additive and guarded: a no-op unless ``engine.on_event`` is set, so every existing
    run path is byte-identical. Carries positions + the NL message + capture (no score —
    the running score is not final until the sub-game ends; the web layer adds it there).
    """
    on_event = getattr(engine, "on_event", None)
    if on_event is None:
        return
    board = entry["board"]
    on_event(
        {
            "type": "turn",
            "sub_game": entry["sub_game"],
            "turn": entry["turn"],
            "role": entry["role"],
            "message": entry["nl_message"],
            "tool": entry.get("tool"),
            "cop_pos": list(board.get("cop", [])),
            "thief_pos": list(board.get("thief", [])),
            "barriers": board.get("barriers", []),
            "coord_flagged": bool(entry.get("coord_flagged", False)),
            "captured": captured,
        }
    )


async def _call_tool(client: Any, name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Call an MCP tool through the FastMCP client and return its structured data."""
    result = await client.call_tool(name, args)
    data = getattr(result, "data", None)
    return data if isinstance(data, dict) else {"raw": data}


async def _reconcile_state(engine: Any, role: str) -> None:
    """Mirror the acting server's truth to all servers (cloud state-sync; no-op local).

    Looks up the engine's optional ``state_sync`` (set only by the cloud builder);
    when present it pulls ``role``'s server board into the engine's canonical state
    and pushes it to both servers so observations stay consistent (E6). Local runs
    share one in-process state and have no ``state_sync``, so this is a no-op.
    """
    state_sync = getattr(engine, "state_sync", None)
    if state_sync is not None:
        await state_sync.reconcile(engine.state, role)


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
    suggestion = tactics.suggest(engine, role, estimate)
    use_hint = bool(engine.config.get("strategy.enabled", default=False))
    prompt = agent.build_prompt(
        observation, opponent_message, suggestion=tactics.hint(suggestion) if use_hint else None
    )
    decision = await engine.gemini.ask(role, prompt)
    message = decision.get("message") or f"({role} stays quiet)"
    coord_flagged = engine.guard.is_flagged(message)
    tool_name, tool_args = _normalize_action(decision, role)
    action_result = await _call_tool(client, tool_name, tool_args)
    if not action_result.get("ok", True):
        _LOG.warning("illegal move for %s; applying heuristic fallback", role)
        tool_name, tool_args = tactics.to_action(role, suggestion)
        action_result = await _call_tool(client, tool_name, tool_args)
    await _reconcile_state(engine, role)
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
    _emit_turn_log(engine, entry)
    _emit_event(engine, entry, captured)
    return {"message": message, "captured": captured, "board": board, "entry": entry}
