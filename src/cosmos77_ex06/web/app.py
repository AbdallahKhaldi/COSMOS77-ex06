"""Build the Starlette app for the live match console (factory form for tests).

A standalone ASGI app (its own port) — NOT mounted under FastMCP — serving one HTML
page, JSON endpoints, an SSE stream, and the static assets. Config + the MatchFeed +
a Gatekeeper + the reports dir are stored on ``app.state`` so handlers reach them
without globals. No game logic here (Rule 2); see web.feed / web.runner / web.match.
"""

from __future__ import annotations

from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Mount, Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from cosmos77_ex06.shared.config import Config
from cosmos77_ex06.shared.gatekeeper import Gatekeeper
from cosmos77_ex06.web import pages, routes
from cosmos77_ex06.web.feed import MatchFeed

_HERE = Path(__file__).resolve().parent


def build_app(config: Config | None = None, feed: MatchFeed | None = None) -> Starlette:
    """Construct the console app; inject ``config`` / ``feed`` (tests pass fakes)."""
    config = config or Config()
    feed = feed or MatchFeed()
    repo_root = config.config_dir.parent
    app = Starlette(
        routes=[
            Route("/", pages.index, methods=["GET"]),
            Route("/challenge", pages.challenge, methods=["GET"]),
            Route("/api/our-info", routes.our_info, methods=["GET"]),
            Route("/api/run", routes.run, methods=["POST"]),
            Route("/api/events/{run_id}", routes.events, methods=["GET"]),
            WebSocketRoute("/api/ws/{run_id}", routes.ws_events),
            Mount("/static", StaticFiles(directory=str(_HERE / "static")), name="static"),
        ],
    )
    app.state.config = config
    app.state.feed = feed
    app.state.gatekeeper = Gatekeeper(repo_root / "results")
    app.state.reports_dir = repo_root / "reports"
    app.state.templates = Jinja2Templates(directory=str(_HERE / "templates"))
    return app
