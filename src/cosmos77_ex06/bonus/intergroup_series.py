"""Run the full 6-sub-game inter-group series vs NajAmjad + the K3 digest (E12).

Role schedule (treaty): sub-games 1-3 NajAmjad (group_1) cop / COSMOS77 (group_2) thief; 4-6 swap.
We drive OUR engine against the right foreign server each sub-game and emit NajAmjad's AGREED entry
shape verbatim — ``{sub_game, cop_team, thief_team, outcome, cop_points, thief_points, cop_url,
thief_url}`` (no nulls/floats) — so the K3 SHA-256 digest (sort_keys, compact) matches byte-for-byte.
Returns ``{sub_games, digest}``.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus.intergroup import digest, play_sub_game
from cosmos77_ex06.bonus.remote import RemoteMoveSource
from cosmos77_ex06.shared.config import Config


def _entry(index: int, our_role: str, winner: str, teams: dict, urls: dict, config: Config) -> dict:
    """Build NajAmjad's agreed sub_games entry from the sub-game winner (their exact shape)."""
    if our_role == "cop":
        cop_team, thief_team = teams["our"], teams["their"]
        cop_url, thief_url = urls["our_cop"], urls["their_thief"]
    else:
        cop_team, thief_team = teams["their"], teams["our"]
        cop_url, thief_url = urls["their_cop"], urls["our_thief"]
    if winner == "cop":
        cop_pts, thief_pts = (
            int(config.get("scoring.cop_win")),
            int(config.get("scoring.thief_loss")),
        )
    else:
        cop_pts, thief_pts = (
            int(config.get("scoring.cop_loss")),
            int(config.get("scoring.thief_win")),
        )
    return {
        "sub_game": index,
        "cop_team": cop_team,
        "thief_team": thief_team,
        "outcome": "cop_wins" if winner == "cop" else "thief_wins",
        "cop_points": cop_pts,
        "thief_points": thief_pts,
        "cop_url": cop_url,
        "thief_url": thief_url,
    }


async def run_series(
    config: Config,
    teams: dict[str, str],
    urls: dict[str, str],
    their_cop: RemoteMoveSource,
    their_thief: RemoteMoveSource,
    *,
    opening: dict[str, tuple] | None = None,
    on_event: Any = None,
) -> dict[str, Any]:
    """Play all 6 role-swap sub-games; return the AGREED ``sub_games`` + the K3 digest.

    ``teams = {"our","their"}`` (group strings); ``urls = {"our_cop","our_thief","their_cop",
    "their_thief"}`` (the exact /mcp/ strings both sides hash).
    """
    sub_games: list[dict[str, Any]] = []
    for index in range(1, 7):
        our_role = "thief" if index <= 3 else "cop"
        opponent = their_cop if our_role == "thief" else their_thief
        result = await play_sub_game(
            config, index, our_role, opponent, opening=opening, on_event=on_event
        )
        sub_games.append(_entry(index, our_role, result["winner"], teams, urls, config))
    return {"sub_games": sub_games, "digest": digest(sub_games)}
