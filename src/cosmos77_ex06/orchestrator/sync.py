"""Cloud state-sync: mirror the engine's canonical board to BOTH MCP servers (E6).

In a CLOUD run the cop and thief servers are SEPARATE processes, each holding its
own :class:`GameState` (built independently by ``make_state``). Without mirroring,
the thief server never sees the cop's move and the two boards DIVERGE. This module
closes that gap: the orchestrator (MCP Client) owns the authoritative state and,
after every turn, pushes the canonical board to both servers via the ``sync_state``
MCP tool (orchestrator-token only). Each server overwrites its internal ground
truth, then STILL redacts to a partial view in ``get_local_observation`` (E4 holds:
``sync_state`` sets truth; the LLM only ever sees the redacted observation).

Local runs share one in-process state via ``_StateProxy`` and so skip this entirely
(the no-op :class:`NullStateSync`), keeping the Phase-4 behaviour byte-identical.
"""

from __future__ import annotations

import asyncio
from typing import Any, Protocol

from cosmos77_ex06.game import rules
from cosmos77_ex06.game.state import GameState


class StateSyncError(RuntimeError):
    """A server would not accept the canonical mirror — the runner should void + rerun (E13)."""


def _data(result: Any) -> dict[str, Any]:
    """Return a tool result's structured ``.data`` mapping (or empty)."""
    data = getattr(result, "data", None)
    return data if isinstance(data, dict) else {}


def _matches(echo: dict[str, Any], payload: dict[str, Any]) -> bool:
    """True when a server's read-back agrees with the pushed board on the live fields."""
    for fld in ("current_role", "move_number", "cop_pos", "thief_pos"):
        if echo.get(fld) != payload.get(fld):
            return False
    ec = {tuple(b) for b in echo.get("barriers", [])}
    pc = {tuple(b) for b in payload.get("barriers", [])}
    return ec == pc


class StateSync(Protocol):
    """Reconciles ground truth across the MCP servers after a role has acted."""

    async def push(self, state: GameState) -> None:
        """Mirror ``state`` to every server (e.g. at sub-game reset)."""

    async def reconcile(self, engine_state: GameState, acted_role: str) -> None:
        """Pull the acting server's truth into ``engine_state`` and mirror it everywhere."""


class NullStateSync:
    """No-op sync for LOCAL runs (servers already share one in-process state)."""

    async def push(self, state: GameState) -> None:
        """Do nothing — the shared in-process state needs no mirroring."""

    async def reconcile(self, engine_state: GameState, acted_role: str) -> None:
        """Do nothing — the shared ``_StateProxy`` already keeps both servers consistent."""


# Fields the ACTING server is authoritative for (board effects of its own tool).
# Turn-progression fields (``current_role`` / ``move_number``) are OWNED BY THE
# ENGINE — a per-server tool (e.g. ``place_barrier``) leaves them untouched and the
# engine's force-progress correction must win, so reconcile must NOT pull them back.
_SERVER_OWNED_FIELDS = ("cop_pos", "thief_pos", "barriers", "barriers_used", "status")


class ClientStateSync:
    """Reconcile ground truth across two SEPARATE-process servers (cloud, E6).

    Holds the orchestrator-token FastMCP clients for both roles. After a role acts on
    its OWN server, :meth:`reconcile` MERGES that server's board *effects* (positions,
    barriers, status) into the engine's canonical state while the ENGINE keeps sole
    ownership of turn-progression (``current_role`` / ``move_number``), then PUSHES the
    merged engine state to every server (``sync_state``) so all boards match and the
    next role can act. This preserves the documented invariant — the engine owns the
    authoritative :class:`GameState` — and stops a stale server (e.g. after a
    ``place_barrier`` turn that never advanced the turn) from overwriting the engine's
    force-progress fix and deadlocking the next role. Servers still redact in
    ``get_local_observation`` (E4): these tools are orchestrator-only, never the LLM.
    """

    def __init__(self, clients: dict[str, Any], *, timeout: float = 10.0, retries: int = 2) -> None:
        self._clients = clients
        self._timeout = timeout
        self._retries = retries

    async def _call(self, client: Any, name: str, args: dict[str, Any]) -> Any:
        """One cross-process tool call, time-bounded so a hung server can't freeze the game."""
        return await asyncio.wait_for(client.call_tool(name, args), self._timeout)

    async def _push_one(self, role: str, client: Any, payload: dict[str, Any]) -> None:
        """Mirror to ONE server and confirm it took; retry, then raise on persistent drift."""
        for _ in range(self._retries + 1):
            await self._call(client, "sync_state", {"state": payload})
            echo = _data(await self._call(client, "get_full_state", {}))
            if _matches(echo, payload):
                return
        raise StateSyncError(
            f"{role} server rejected the mirror after {self._retries + 1} attempts"
        )

    async def _mirror(self, payload: dict[str, Any]) -> None:
        """Push ``payload`` to every server and verify each one adopted it (self-healing)."""
        for role, client in self._clients.items():
            await self._push_one(role, client, payload)

    async def push(self, state: GameState) -> None:
        """Mirror the canonical ``state`` to both servers (sub-game reset, E6)."""
        await self._mirror(state.to_dict())

    async def reconcile(self, engine_state: GameState, acted_role: str) -> None:
        """Merge the acting server's board effects, advance the turn, then mirror.

        Adopts only the fields the acting server is authoritative for (positions,
        barriers, barriers_used, status). The ENGINE then OWNS turn-progression: it
        advances ``current_role`` to the next role and bumps ``move_number`` once the
        last role in ``turn_order`` has acted — uniformly, whether that role MOVED or
        placed a BARRIER (``place_barrier`` never advances the turn server-side). The
        merged engine state is pushed to BOTH servers so every board agrees and the
        next role's ``apply_move`` turn-order gate passes (no deadlock, no divergence).
        """
        result = await self._call(self._clients[acted_role], "get_full_state", {})
        canonical = GameState.from_dict(_data(result))
        for fld in _SERVER_OWNED_FIELDS:
            setattr(engine_state, fld, getattr(canonical, fld))
        order = list(engine_state.turn_order)
        engine_state.current_role = rules.next_role(acted_role, order)
        if acted_role == order[-1]:
            engine_state.move_number += 1
        await self._mirror(engine_state.to_dict())
