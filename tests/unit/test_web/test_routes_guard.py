"""Wave-4 resource guard — the console refuses new games past max_concurrent_runs."""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient


def test_run_rejects_when_at_capacity_429(
    app_and_feed: tuple[Any, Any, Any], monkeypatch: Any
) -> None:
    """The concurrency guard refuses new games once max_concurrent_runs is reached."""
    app, feed, _ = app_and_feed
    monkeypatch.setattr(feed, "active_count", lambda: 99)
    response = TestClient(app).post(
        "/api/run", json={"action": "solo", "passphrase": "open-sesame"}
    )
    assert response.status_code == 429
