"""Structured per-turn comms-log tests — proves cloud-MCP comms (E10/E6, rule 9)."""

from __future__ import annotations

import json

from cosmos77_ex06.orchestrator import turn_log

_ENTRY = {
    "sub_game": 2,
    "turn": 14,
    "role": "thief",
    "nl_message": "Heading for the open south corridor; I don't think you've spotted me.",
    "tool": "apply_move",
    "args": {"role": "thief", "direction": "S"},
    "board": {"cop": [1, 4], "thief": [4, 1], "barriers": [], "move": 14},
    "mcp_url": "https://cop-xxxx.fastmcp.app/mcp",
}


def test_record_carries_all_required_fields() -> None:
    rec = turn_log.build_record(_ENTRY)
    for key in ("turn", "role", "message", "tool_call", "resulting_position", "server_url"):
        assert key in rec
    assert rec["server_url"] == "https://cop-xxxx.fastmcp.app/mcp"
    assert rec["message"] == _ENTRY["nl_message"]
    assert rec["resulting_position"] == [4, 1]
    assert rec["tool_call"] == "apply_move(direction=S)"


def test_human_format_includes_url_and_nl_message() -> None:
    line = turn_log.format_record(turn_log.build_record(_ENTRY), "human")
    assert "https://cop-xxxx.fastmcp.app/mcp" in line
    assert "open south corridor" in line
    assert "apply_move(direction=S)" in line
    assert "pos=(4, 1)" in line


def test_jsonl_format_roundtrips_with_url_and_message() -> None:
    line = turn_log.format_record(turn_log.build_record(_ENTRY), "jsonl")
    parsed = json.loads(line)
    assert parsed["server_url"] == "https://cop-xxxx.fastmcp.app/mcp"
    assert parsed["message"] == _ENTRY["nl_message"]
    assert parsed["resulting_position"] == [4, 1]


def test_server_url_can_be_suppressed() -> None:
    rec = turn_log.build_record(_ENTRY, show_server_url=False)
    assert "server_url" not in rec


def test_log_never_leaks_token() -> None:
    # The auth token value must never appear; only auth=ok is recorded (E2).
    entry = dict(_ENTRY, args={"role": "thief", "direction": "S", "token": "SECRET-TOKEN-123"})
    rec = turn_log.build_record(entry)
    line = turn_log.format_record(rec, "human")
    assert "SECRET-TOKEN-123" not in line
    assert rec["auth"] == "ok"
    # role + token are stripped from the rendered tool call, direction survives.
    assert "token=" not in rec["tool_call"]
    assert "role=" not in rec["tool_call"]


def test_barrier_tool_call_formats_coordinates() -> None:
    entry = dict(_ENTRY, role="cop", tool="place_barrier", args={"role": "cop", "x": 2, "y": 3})
    rec = turn_log.build_record(entry)
    assert rec["tool_call"] == "place_barrier(x=2, y=3)"
