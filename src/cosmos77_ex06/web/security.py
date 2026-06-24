"""Passphrase gate for the live web console — every run is gated (Rule 9).

The expected passphrase lives ONLY in the ``WEB_PASSPHRASE`` env var (never in config
or the repo). An unset OR mismatched value fails CLOSED, so a misconfigured server
starts no runs. Comparison is constant-time to avoid leaking the passphrase by timing.
"""

from __future__ import annotations

import hmac
from typing import Any


def passphrase_ok(supplied: str, config: Any) -> bool:
    """True only when ``supplied`` matches ``WEB_PASSPHRASE`` (constant-time, fail-closed)."""
    expected = config.env("WEB_PASSPHRASE") if config is not None else None
    if not expected or not supplied:
        return False
    return hmac.compare_digest(str(supplied), str(expected))
