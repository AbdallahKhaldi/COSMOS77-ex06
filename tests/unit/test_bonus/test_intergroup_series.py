"""6-game series runner — emits NajAmjad's AGREED sub_games entry shape (digest-critical, E12)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from cosmos77_ex06.bonus import intergroup_series
from cosmos77_ex06.bonus.intergroup import digest
from cosmos77_ex06.shared.config import Config


class _Opp:
    def __init__(self, line: str) -> None:
        self._line = line

    async def request_move(self, observation: dict[str, Any]) -> str:
        return self._line


_TEAMS = {"our": "COSMOS77", "their": "NajAmjad"}
_URLS = {
    "our_cop": "https://c77-cop/mcp/",
    "our_thief": "https://c77-thief/mcp/",
    "their_cop": "https://naj-cop/mcp/",
    "their_thief": "https://naj-thief/mcp/",
}
_KEYS = {
    "sub_game",
    "cop_team",
    "thief_team",
    "outcome",
    "cop_points",
    "thief_points",
    "cop_url",
    "thief_url",
}


async def test_series_emits_agreed_entry_shape() -> None:
    cfg = Config()
    cop = _Opp("[INTENT: MOVE] The cop edges north-west.")
    thief = _Opp("[INTENT: MOVE] The thief edges south.")
    res = await intergroup_series.run_series(
        cfg, _TEAMS, _URLS, cop, thief, opening={"cop": (2, 2), "thief": (0, 0)}
    )
    sg = res["sub_games"]
    assert len(sg) == 6 and len(res["digest"]) == 64
    for entry in sg:
        assert set(entry) == _KEYS
        assert isinstance(entry["sub_game"], int) and isinstance(entry["cop_points"], int)
        assert entry["outcome"] in ("cop_wins", "thief_wins")
        assert (entry["cop_points"], entry["thief_points"]) in ((20, 5), (5, 10))
    assert sg[0]["cop_team"] == "NajAmjad" and sg[0]["thief_team"] == "COSMOS77"
    assert sg[3]["cop_team"] == "COSMOS77" and sg[3]["thief_team"] == "NajAmjad"


def test_digest_equals_their_exact_sha256_formula() -> None:
    sub = [
        {
            "sub_game": 1,
            "cop_team": "NajAmjad",
            "thief_team": "COSMOS77",
            "outcome": "cop_wins",
            "cop_points": 20,
            "thief_points": 5,
            "cop_url": "https://a/mcp/",
            "thief_url": "https://b/mcp/",
        }
    ]
    blob = json.dumps(sub, sort_keys=True, separators=(",", ":")).encode("utf-8")
    assert digest(sub) == hashlib.sha256(blob).hexdigest()
