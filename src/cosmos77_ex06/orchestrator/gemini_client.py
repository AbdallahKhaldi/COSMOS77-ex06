"""Thin wrapper over google-genai 2.9.0 with NATIVE MCP tool-calling (E3).

``GeminiClient.ask`` is **async** and builds a ``GenerateContentConfig`` whose
``tools`` is the live FastMCP session (``client.session``) so Gemini sees the
server's ``@mcp.tool`` functions as callable tools; the model returns a free
natural-language message plus a proposed tool call. Because google-genai 2.9.0
raises ``UnsupportedFunctionError`` if an MCP session is passed to the SYNCHRONOUS
``client.models.generate_content`` (the check fires before the AFC-disable
branch), this client uses the ASYNC path ``client.aio.models.generate_content``.
Every call routes through the Gatekeeper (token/cost ledger, secret scrub). The
real ``google.genai.Client`` is dependency-injectable via ``client_factory`` so
the unit suite mocks it — no live calls (Rule 6).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def _default_client_factory(api_key: str | None) -> Any:  # pragma: no cover - real SDK
    """Construct the real ``google.genai.Client`` (lazy import; never hit in tests)."""
    from google import genai

    return genai.Client(api_key=api_key)


class GeminiClient:
    """Wraps the LLM call; ``client_factory`` makes it mockable (E3, Rule 6)."""

    def __init__(
        self,
        config: Config,
        gatekeeper: Gatekeeper,
        client_factory: Callable[[str | None], Any] = _default_client_factory,
    ) -> None:
        self.config = config
        self.gatekeeper = gatekeeper
        self.model = str(config.get("llm.model"))
        self.temperature = float(config.get("llm.temperature"))
        self._client_factory = client_factory
        self._client: Any = None
        self._meter: dict[str, dict[str, int]] = {}

    def _client_obj(self) -> Any:
        """Lazily build (and cache) the underlying genai client."""
        if self._client is None:
            self._client = self._client_factory(self.config.env("GEMINI_API_KEY"))
        return self._client

    def _build_config(self, mcp_session: Any) -> Any:
        """Build a ``GenerateContentConfig`` for native MCP tool-calling."""
        from google.genai import types

        return types.GenerateContentConfig(
            tools=[mcp_session],
            temperature=self.temperature,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

    async def ask(self, role: str, prompt: str, mcp_session: Any) -> dict[str, Any]:
        """Ask Gemini for one turn; return ``{message, tool, args}`` and meter the call.

        The live MCP ``session`` is passed as the tool source (native MCP
        tool-calling). google-genai forbids MCP sessions on the SYNCHRONOUS API,
        so this awaits the async path ``client.aio.models.generate_content``.
        Auto-calling is disabled so the *engine* logs and routes the proposed
        tool call (full transcript observability, PRD §4).
        """
        client = self._client_obj()
        cfg = self._build_config(mcp_session)
        response = await client.aio.models.generate_content(
            model=self.model, contents=prompt, config=cfg
        )
        return self._parse_and_meter(role, prompt, response)

    def _parse_and_meter(self, role: str, prompt: str, response: Any) -> dict[str, Any]:
        """Extract the NL message + first tool call from a response and record cost."""
        message = (getattr(response, "text", None) or "").strip()
        calls = getattr(response, "function_calls", None) or []
        tool, args = (None, {})
        if calls:
            tool = getattr(calls[0], "name", None)
            args = dict(getattr(calls[0], "args", {}) or {})
        usage = getattr(response, "usage_metadata", None)
        tokens = int(getattr(usage, "total_token_count", 0) or 0) if usage else 0
        acc = self._meter.setdefault(role, {"calls": 0, "tokens": 0})
        acc["calls"] += 1
        acc["tokens"] += tokens
        self.gatekeeper.record(
            f"llm_{role}",
            {"calls": acc["calls"], "tokens": acc["tokens"], "model": self.model},
        )
        return {"role": role, "message": message, "tool": tool, "args": args}
