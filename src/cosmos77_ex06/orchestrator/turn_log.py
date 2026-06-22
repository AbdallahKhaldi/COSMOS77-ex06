"""Structured per-turn CLI comms log — the "proof of cloud-MCP comms" (E10/E6).

The orchestrator emits ONE record per agent action carrying turn#, role, the full
free natural-language message, the MCP tool call + args, the resulting position,
and the **MCP server URL** the call hit (``http://localhost:…`` locally, the
``https://…`` cloud URL under ``--cloud``). These lines are the auditable text
evidence that the two autonomous agents really conversed over the MCP servers
(PRD_gui §5). Logging is purely ADDITIVE: it reads the already-built transcript
entry and never mutates game state. Two config-selected renderings — ``human``
(terminal/README capture) and ``jsonl`` (machine-checkable) — are supported, and
the auth token value is never printed (only ``auth=ok``; rule 9 / E2).
"""

from __future__ import annotations

import json
from typing import Any


def _resulting_position(entry: dict[str, Any]) -> list[int]:
    """The acting role's cell after its move (from the board snapshot)."""
    board = entry.get("board", {})
    return list(board.get(entry["role"], []))


def build_record(entry: dict[str, Any], *, show_server_url: bool = True) -> dict[str, Any]:
    """Assemble the structured turn record (E10 required fields) from ``entry``."""
    record: dict[str, Any] = {
        "sub_game": entry.get("sub_game"),
        "turn": entry.get("turn"),
        "role": entry.get("role"),
        "message": entry.get("nl_message", ""),
        "tool_call": format_tool_call(entry.get("tool"), entry.get("args", {})),
        "resulting_position": _resulting_position(entry),
        "auth": "ok",
    }
    if show_server_url:
        record["server_url"] = entry.get("mcp_url", "")
    return record


#: Only these argument names are ever rendered; everything else (``role``, any
#: ``token``/secret) is dropped so the log can never leak the auth token (rule 9).
_SHOWN_ARGS = ("direction", "x", "y")


def format_tool_call(tool: str | None, args: dict[str, Any]) -> str:
    """Render a tool invocation as ``name(k=v, ...)`` over whitelisted args only."""
    inner = ", ".join(f"{k}={args[k]}" for k in _SHOWN_ARGS if k in args)
    return f"{tool or 'noop'}({inner})"


def format_human(record: dict[str, Any]) -> str:
    """Render a record as the human-readable terminal/README line (PRD §5.2)."""
    head = (
        f"[sub {record.get('sub_game')} | turn {record.get('turn'):0>3} | "
        f"{str(record.get('role', '')).upper()}]"
    )
    url = record.get("server_url")
    head += (
        f" url={url} auth={record.get('auth', 'ok')}"
        if url
        else f" auth={record.get('auth', 'ok')}"
    )
    return (
        f"{head}\n  msg={record.get('message', '')!r}\n"
        f"  tool={record.get('tool_call')} -> pos={tuple(record.get('resulting_position', []))}"
    )


def format_record(record: dict[str, Any], fmt: str) -> str:
    """Render ``record`` in the configured format (``human`` or ``jsonl``)."""
    if fmt == "jsonl":
        return json.dumps(record, sort_keys=True)
    return format_human(record)
