"""RemoteMoveSource — calls a foreign request_move via an injected fake client (no network)."""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus.remote import RemoteMoveSource


class _FakeResult:
    def __init__(self, text: str) -> None:
        self.data = text


class _FakeClient:
    def __init__(self, text: str, calls: list) -> None:
        self._text, self._calls = text, calls

    async def __aenter__(self) -> _FakeClient:
        return self

    async def __aexit__(self, *a: Any) -> bool:
        return False

    async def call_tool(self, name: str, args: dict) -> _FakeResult:
        self._calls.append((name, args))
        return _FakeResult(self._text)


async def test_request_move_passes_observation_and_token() -> None:
    calls: list = []
    src = RemoteMoveSource(
        "https://x/mcp/",
        "tok",
        client_factory=lambda u, t: _FakeClient("[INTENT: MOVE] edges east.", calls),
    )
    out = await src.request_move({"role": "cop", "turn": 0})
    assert out == "[INTENT: MOVE] edges east."
    assert calls == [
        ("request_move", {"observation": {"role": "cop", "turn": 0}, "auth_token": "tok"})
    ]
