"""The two public pages render without a passphrase (index + challenger briefing)."""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient


def test_index_and_challenge_pages_render(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    client = TestClient(app)
    assert "COSMOS77" in client.get("/").text
    briefing = client.get("/challenge")
    assert briefing.status_code == 200 and "CHALLENGE" in briefing.text.upper()
