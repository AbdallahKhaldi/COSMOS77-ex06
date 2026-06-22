"""Transient-error retry + inter-call pacing for the Gemini client (Rule 4).

The Phase-7 full game makes hundreds of free-tier calls, so a robust 429 policy is
critical. :class:`RetryPolicy` retries HTTP 429 / RESOURCE_EXHAUSTED / 5xx errors,
preferring the SERVER'S suggested wait: google-genai surfaces a ``RetryInfo`` with
a ``retryDelay`` (e.g. ``"7s"`` or ``"1.5s"``) inside the error payload, and we
parse it and sleep exactly that long instead of guessing. With no suggested delay
we fall back to exponential backoff (``base * 2**attempt``). An optional
``min_call_interval_seconds`` PACES successive calls to stay under the free-tier
rate. Behaviour is identical to plain backoff when no 429 occurs (no extra sleeps).
"""

from __future__ import annotations

import asyncio
import re
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")

# Tight, high-signal markers for the gemini/grpc transient errors we mean to retry.
# We deliberately avoid loose words (e.g. a bare "unavailable") that could appear in
# a non-retryable message and cause needless retries; the structured code check below
# is the PRIMARY signal, and the exception TYPE NAME is matched separately from the
# free-text message so "503 Service Unavailable" still retries via the type/status.
_RETRY_MARKERS = ("429", "resource_exhausted", "resourceexhausted", "rate_limit")
_TYPE_MARKERS = ("resourceexhausted", "serviceunavailable", "deadlineexceeded", "unavailable")
_DELAY_RE = re.compile(r"retrydelay['\"]?\s*[:=]\s*['\"]?\s*([0-9]+(?:\.[0-9]+)?)\s*s", re.I)


def is_transient(exc: Exception) -> bool:
    """True for HTTP 429 / ResourceExhausted / 5xx-style transient SDK errors.

    The structured ``code``/``status_code`` (429 or 5xx) is the primary signal.
    Failing that we match tight markers in the message text and the exception type
    name separately, so a non-retryable error whose free text merely contains a
    word like "unavailable" is not retried.
    """
    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    if isinstance(code, int) and (code == 429 or 500 <= code < 600):
        return True
    type_name = type(exc).__name__.lower()
    if any(marker in type_name for marker in _TYPE_MARKERS):
        return True
    text = str(exc).lower()
    return any(marker in text for marker in _RETRY_MARKERS)


def parse_retry_delay(exc: Exception) -> float | None:
    """Extract the server's ``RetryInfo.retryDelay`` seconds, if present.

    Handles both a structured ``retry_delay`` attribute (``.seconds``) and the
    string form google-genai embeds in the error message (``'retryDelay': '7s'``).
    Returns ``None`` when the server suggested no delay.
    """
    structured = getattr(exc, "retry_delay", None)
    seconds = getattr(structured, "seconds", None)
    if isinstance(seconds, int | float):
        return float(seconds)
    match = _DELAY_RE.search(str(exc))
    return float(match.group(1)) if match else None


class RetryPolicy:
    """Config-driven retry-with-pacing wrapper around an async LLM call."""

    def __init__(
        self,
        max_retries: int,
        retry_base_seconds: float,
        min_call_interval_seconds: float = 0.0,
        sleep: Callable[[float], Awaitable[None]] | None = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_retries = max_retries
        self.retry_base_seconds = retry_base_seconds
        self.min_call_interval_seconds = min_call_interval_seconds
        self._sleep_override = sleep
        self._monotonic = monotonic
        self._last_call_at: float | None = None

    async def _sleep(self, seconds: float) -> None:
        """Sleep ``seconds`` via the injected hook or live ``asyncio.sleep``.

        Resolving ``asyncio.sleep`` at call time (not as a bound default) keeps the
        retry timing monkeypatchable in the suite (``llm_retry.asyncio.sleep``).
        """
        if self._sleep_override is not None:
            await self._sleep_override(seconds)
        else:
            await asyncio.sleep(seconds)

    async def _pace(self) -> None:
        """Sleep so successive calls are >= ``min_call_interval_seconds`` apart."""
        interval = self.min_call_interval_seconds
        if interval <= 0:
            return
        if self._last_call_at is not None:
            elapsed = self._monotonic() - self._last_call_at
            if elapsed < interval:
                await self._sleep(interval - elapsed)
        self._last_call_at = self._monotonic()

    def _backoff_for(self, exc: Exception, attempt: int) -> float:
        """The wait before the next attempt: server ``retryDelay`` or backoff."""
        suggested = parse_retry_delay(exc)
        if suggested is not None:
            return suggested
        return self.retry_base_seconds * (2**attempt)

    async def run(self, call: Callable[[], Awaitable[T]]) -> T:
        """Invoke ``call`` with pacing; retry transient errors per the policy."""
        for attempt in range(self.max_retries + 1):
            await self._pace()
            try:
                return await call()
            except Exception as exc:
                if attempt >= self.max_retries or not is_transient(exc):
                    raise
                await self._sleep(self._backoff_for(exc, attempt))
        raise RuntimeError("unreachable: retry loop exhausted")  # pragma: no cover
