"""Thin wrapper over google-genai 2.9.0 using STRUCTURED-OUTPUT decisions (E3).

``GeminiClient.ask`` (async) builds a ``GenerateContentConfig`` asking Gemini for
one JSON object (``response_mime_type="application/json"`` + a role-conditional
``response_schema``): a free natural-language ``message`` plus an ``action`` (move,
or — cop only — barrier). The *engine* executes that action via the FastMCP server
tools (``apply_move`` / ``place_barrier``), preserving Server/Client separation and
MCP tool use. We do NOT pass the live MCP session as ``tools=[session]``: google-genai 2.9.0 deep-copies the config
per request, and a live FastMCP ``ClientSession`` holds an ``_asyncio.Future`` that
cannot be deep-copied (``cannot pickle '_asyncio.Future'``); structured output
sidesteps that. Uses the ASYNC path ``client.aio.models.generate_content``; the real
client is dependency-injectable via ``client_factory`` so the suite mocks it (Rule
6). Every call routes through the Gatekeeper; transient free-tier failures (429 /
ResourceExhausted / 5xx) retry with exponential backoff (config-driven; Rule 4).
"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from cosmos77_ex06.orchestrator.llm_retry import RetryPolicy
from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper

_DIRECTIONS = ["N", "S", "E", "W", "NE", "NW", "SE", "SW", "STAY"]
_ROLE_ACTIONS = {"cop": ["move", "barrier"], "thief": ["move"]}
_FALLBACK = {"message": "", "action": {"type": "move", "direction": "STAY"}}


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
        self.max_retries = int(config.get("llm.max_retries", default=4))
        self.retry_base_seconds = float(config.get("llm.retry_base_seconds", default=2.0))
        self.retry = RetryPolicy(
            self.max_retries,
            self.retry_base_seconds,
            float(config.get("llm.min_call_interval_seconds", default=0.0)),
        )
        self._client_factory = client_factory
        self._client: Any = None
        self._meter: dict[str, dict[str, int]] = {}

    def _client_obj(self) -> Any:
        """Lazily build (and cache) the underlying genai client."""
        if self._client is None:
            self._client = self._client_factory(self.config.env("GEMINI_API_KEY"))
        return self._client

    def _build_config(self, role: str) -> Any:
        """Build a ``GenerateContentConfig`` for a role-conditional JSON decision."""
        from google.genai import types

        t = types.Type
        s = types.Schema
        action = s(
            type=t.OBJECT,
            properties={
                "type": s(type=t.STRING, enum=_ROLE_ACTIONS.get(role, ["move"])),
                "direction": s(type=t.STRING, enum=_DIRECTIONS),
                "x": s(type=t.INTEGER),
                "y": s(type=t.INTEGER),
            },
            required=["type"],
        )
        schema = s(
            type=t.OBJECT,
            properties={"message": s(type=t.STRING), "action": action},
            required=["message", "action"],
        )
        budget = int(self.config.get("llm.thinking_budget", default=0))
        return types.GenerateContentConfig(
            temperature=self.temperature,
            response_mime_type="application/json",
            response_schema=schema,
            thinking_config=types.ThinkingConfig(thinking_budget=budget),
        )

    async def ask(self, role: str, prompt: str) -> dict[str, Any]:
        """Ask Gemini for one JSON decision; return ``{role, message, tool, args}``.

        No live MCP session enters the config (google-genai 2.9.0 cannot deep-copy
        it). The engine executes the chosen action via the MCP server tools,
        preserving Server/Client separation and full transcript observability.
        """
        return self._parse_and_meter(role, await self._generate_with_retry(role, prompt))

    async def _generate_with_retry(self, role: str, prompt: str) -> Any:
        """Await the async generate call, retrying transient 429/5xx (RetryPolicy)."""
        client, cfg = self._client_obj(), self._build_config(role)

        async def _call() -> Any:
            return await client.aio.models.generate_content(
                model=self.model, contents=prompt, config=cfg
            )

        return await self.retry.run(_call)

    def _parse_and_meter(self, role: str, response: Any) -> dict[str, Any]:
        """Parse the JSON decision into ``{role, message, tool, args}`` and record cost."""
        decision = _parse_decision(getattr(response, "text", None))
        message = str(decision.get("message", "")).strip()
        tool, args = _action_to_tool(decision.get("action") or {})
        usage = getattr(response, "usage_metadata", None)
        tokens = int(getattr(usage, "total_token_count", 0) or 0) if usage else 0
        acc = self._meter.setdefault(role, {"calls": 0, "tokens": 0})
        acc["calls"] += 1
        acc["tokens"] += tokens
        self.gatekeeper.record(f"llm_{role}", {**acc, "model": self.model})
        return {"role": role, "message": message, "tool": tool, "args": args}


def _parse_decision(text: str | None) -> dict[str, Any]:
    """Parse ``response.text`` as JSON, falling back to a safe STAY decision."""
    try:
        parsed = json.loads(text or "")
        return parsed if isinstance(parsed, dict) else dict(_FALLBACK)
    except (ValueError, TypeError):
        return dict(_FALLBACK)


def _action_to_tool(action: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Map a parsed ``action`` object onto the ``(tool, args)`` shape turn.py expects."""
    if str(action.get("type", "")).lower() == "barrier":
        return "place_barrier", {"x": int(action.get("x", 0)), "y": int(action.get("y", 0))}
    return "apply_move", {"direction": str(action.get("direction", "STAY"))}
