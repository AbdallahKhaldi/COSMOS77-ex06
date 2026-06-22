"""Tests for the rate-limit RetryPolicy: respect retryDelay, pace, backoff (Rule 4)."""

from __future__ import annotations

import asyncio

import pytest

from cosmos77_ex06.orchestrator.llm_retry import (
    RetryPolicy,
    is_transient,
    parse_retry_delay,
)


class _RetryInfo:
    """A structured RetryInfo-like object exposing ``.seconds`` (proto style)."""

    def __init__(self, seconds: float) -> None:
        self.seconds = seconds


class _Err429(Exception):  # noqa: N818 - mimics a provider 429 error
    """A 429-like error carrying a structured ``retry_delay``."""

    def __init__(self, seconds: float) -> None:
        super().__init__("429 RESOURCE_EXHAUSTED")
        self.retry_delay = _RetryInfo(seconds)


def test_is_transient_detects_429_and_5xx() -> None:
    assert is_transient(RuntimeError("429 RESOURCE_EXHAUSTED"))
    assert is_transient(type("E", (Exception,), {"code": 503})())
    assert not is_transient(ValueError("bad json"))


def test_is_transient_matches_provider_exception_type_name() -> None:
    """A 5xx whose only signal is the SDK exception type still retries."""
    exc = type("ServiceUnavailable", (Exception,), {})("backend down")
    assert is_transient(exc)


def test_is_transient_ignores_loose_word_in_free_text() -> None:
    """A non-retryable error whose message merely contains 'unavailable' is NOT retried."""
    assert not is_transient(ValueError("the requested feature is currently unavailable"))


def test_parse_retry_delay_from_string_payload() -> None:
    exc = RuntimeError("RESOURCE_EXHAUSTED ... 'retryDelay': '7s' ...")
    assert parse_retry_delay(exc) == 7.0


def test_parse_retry_delay_from_structured_attr() -> None:
    assert parse_retry_delay(_Err429(1.5)) == 1.5


def test_parse_retry_delay_absent() -> None:
    assert parse_retry_delay(RuntimeError("nothing here")) is None


def test_retry_waits_per_retry_delay_then_succeeds() -> None:
    """A 429 carrying retryDelay is retried after waiting EXACTLY that delay."""
    slept: list[float] = []

    async def _sleep(seconds: float) -> None:
        slept.append(seconds)

    attempts = {"n": 0}

    async def _call() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise _Err429(0.001)  # near-zero suggested delay
        return "ok"

    policy = RetryPolicy(max_retries=3, retry_base_seconds=9.0, sleep=_sleep)
    out = asyncio.run(policy.run(_call))
    assert out == "ok"
    assert attempts["n"] == 2
    assert slept == [0.001]  # the SERVER delay, not the 9.0 backoff base


def test_retry_falls_back_to_backoff_without_retry_delay() -> None:
    slept: list[float] = []

    async def _sleep(seconds: float) -> None:
        slept.append(seconds)

    attempts = {"n": 0}

    async def _call() -> str:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("429 rate limit")
        return "ok"

    policy = RetryPolicy(max_retries=3, retry_base_seconds=2.0, sleep=_sleep)
    assert asyncio.run(policy.run(_call)) == "ok"
    assert slept == [2.0]  # base * 2**0


def test_non_transient_error_is_not_retried() -> None:
    async def _call() -> str:
        raise ValueError("permanent")

    policy = RetryPolicy(max_retries=3, retry_base_seconds=0.0)
    with pytest.raises(ValueError, match="permanent"):
        asyncio.run(policy.run(_call))


def test_pacing_sleeps_to_min_interval() -> None:
    """min_call_interval_seconds paces successive calls using a fake clock."""
    slept: list[float] = []
    clock = {"t": 0.0}

    async def _sleep(seconds: float) -> None:
        slept.append(seconds)
        clock["t"] += seconds

    def _mono() -> float:
        return clock["t"]

    async def _call() -> str:
        clock["t"] += 0.1  # the call itself advances time
        return "ok"

    policy = RetryPolicy(
        max_retries=0,
        retry_base_seconds=0.0,
        min_call_interval_seconds=1.0,
        sleep=_sleep,
        monotonic=_mono,
    )
    asyncio.run(policy.run(_call))  # first call: no pacing wait
    asyncio.run(policy.run(_call))  # second call: paced up to 1.0s apart
    assert slept and pytest.approx(sum(slept), abs=1e-6) == 0.9
