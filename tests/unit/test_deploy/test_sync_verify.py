"""Fix B: the cloud state-sync VERIFIES each mirror and voids a server that won't adopt it."""

from __future__ import annotations

from typing import Any

import pytest

from cosmos77_ex06.orchestrator.sync import ClientStateSync, StateSyncError


class _DriftClient:
    """Accepts sync_state but always reports a STALE board — a wedged cloud server."""

    async def call_tool(self, name: str, args: dict[str, Any]) -> Any:
        stale = {
            "current_role": "thief",
            "move_number": 99,
            "cop_pos": [9, 9],
            "thief_pos": [9, 9],
            "barriers": [],
        }
        return type("R", (), {"data": stale if name == "get_full_state" else {}})()


async def test_mirror_raises_on_persistent_drift(make_state: Any) -> None:
    """A server whose read-back never matches the push is voided (E13), not silently trusted."""
    sync = ClientStateSync({"cop": _DriftClient()}, retries=1)
    with pytest.raises(StateSyncError):
        await sync.push(make_state(cop=(1, 1), thief=(2, 2)))
