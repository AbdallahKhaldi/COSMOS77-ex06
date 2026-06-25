"""MatchFeed — per-run event queues bridging a live game to the browser over SSE.

Each run gets a dedicated ``asyncio.Queue`` keyed by ``run_id``. The game's per-turn
``on_event`` hook (plus the runner's meta/game_end/error/done events) publish onto it;
the SSE endpoint drains it. The game coroutine runs on the SAME event loop as the
server (every turn awaits MCP + Gemini I/O), so publishing is a plain ``put_nowait`` —
no cross-thread marshaling — and concurrent visitors never cross streams.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from cosmos77_ex06.shared.config import Config


class MatchFeed:
    """Registry of per-run event queues plus the SSE drain."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[dict[str, Any]]] = {}

    def our_info(self, config: Config) -> dict[str, str]:
        """Public display info — our two live MCP URLs + the console URL (no secrets)."""
        return {
            "cop_url": str(config.get("mcp.cop_url", default="")),
            "thief_url": str(config.get("mcp.thief_url", default="")),
            "web_url": str(config.get("web.public_url", default="")),
        }

    def register(self, run_id: str) -> asyncio.Queue[dict[str, Any]]:
        """Create + store a fresh queue for ``run_id``."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues[run_id] = queue
        return queue

    def drop(self, run_id: str) -> None:
        """Forget ``run_id``'s queue (after its stream ends)."""
        self._queues.pop(run_id, None)

    def has(self, run_id: str) -> bool:
        """True when ``run_id`` is currently registered."""
        return run_id in self._queues

    def active_count(self) -> int:
        """Number of runs currently registered (live games), for the concurrency guard."""
        return len(self._queues)

    def publish(self, run_id: str, event: dict[str, Any]) -> None:
        """Push one event onto ``run_id``'s queue (the on_event target + lifecycle events)."""
        queue = self._queues.get(run_id)
        if queue is not None:
            queue.put_nowait(event)

    async def stream(self, run_id: str) -> AsyncIterator[dict[str, str]]:
        """Async generator of SSE ``data:`` frames for ``run_id``; ends after ``done``."""
        queue = self._queues.get(run_id)
        if queue is None:
            return
        try:
            while True:
                event = await queue.get()
                yield {"data": json.dumps(event)}
                if event.get("type") == "done":
                    break
        finally:
            self.drop(run_id)
