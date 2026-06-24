"""Route tests for the live match console (Starlette TestClient; no real games run)."""

from __future__ import annotations

from typing import Any

from starlette.testclient import TestClient

from cosmos77_ex06.web import routes


def test_index_returns_html(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    response = TestClient(app).get("/")
    assert response.status_code == 200
    assert "Match Console" in response.text


def test_our_info_returns_config_urls(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    body = TestClient(app).get("/api/our-info").json()
    assert body["cop_url"] == "https://our-cop.example/mcp"
    assert body["thief_url"] == "https://our-thief.example/mcp"
    assert body["web_url"] == "https://console.example"


def test_run_rejects_bad_passphrase_403(
    app_and_feed: tuple[Any, Any, Any], monkeypatch: Any
) -> None:
    app, _, _ = app_and_feed
    called: dict[str, bool] = {}

    async def fake_exh(*a: Any, **k: Any) -> None:
        called["ran"] = True

    monkeypatch.setattr(routes.runner, "run_exhibition", fake_exh)
    response = TestClient(app).post(
        "/api/run",
        json={"action": "exhibition", "passphrase": "wrong", "their_thief_url": "https://t/mcp"},
    )
    assert response.status_code == 403
    assert "ran" not in called  # gate refused before any run was scheduled


def test_run_accepts_good_passphrase_returns_run_id(
    app_and_feed: tuple[Any, Any, Any], monkeypatch: Any
) -> None:
    app, _, _ = app_and_feed

    async def fake_exh(*a: Any, **k: Any) -> None:
        return None

    monkeypatch.setattr(routes.runner, "run_exhibition", fake_exh)
    response = TestClient(app).post(
        "/api/run",
        json={
            "action": "exhibition",
            "passphrase": "open-sesame",
            "their_thief_url": "https://their-thief.example/mcp",
            "token": "tok",
        },
    )
    assert response.status_code == 200
    assert "run_id" in response.json()


def test_run_rejects_unknown_action_400(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    response = TestClient(app).post(
        "/api/run", json={"action": "nope", "passphrase": "open-sesame"}
    )
    assert response.status_code == 400


def test_run_rejects_non_https_url_400(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    response = TestClient(app).post(
        "/api/run",
        json={
            "action": "exhibition",
            "passphrase": "open-sesame",
            "their_thief_url": "http://insecure/mcp",
        },
    )
    assert response.status_code == 400


def test_events_unknown_run_id_404(app_and_feed: tuple[Any, Any, Any]) -> None:
    app, _, _ = app_and_feed
    assert TestClient(app).get("/api/events/nope").status_code == 404


def test_run_series_accepts_four_https_urls(
    app_and_feed: tuple[Any, Any, Any], monkeypatch: Any
) -> None:
    app, _, _ = app_and_feed

    async def fake_series(*a: Any, **k: Any) -> None:
        return None

    monkeypatch.setattr(routes.runner, "run_series", fake_series)
    response = TestClient(app).post(
        "/api/run",
        json={
            "action": "series",
            "passphrase": "open-sesame",
            "their_cop_url": "https://their-cop.example/mcp",
            "their_thief_url": "https://their-thief.example/mcp",
            "token": "tok",
        },
    )
    assert response.status_code == 200 and "run_id" in response.json()
