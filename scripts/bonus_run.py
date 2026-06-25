"""Run the inter-group bonus vs NajAmjad over THEIR request_move contract (E12).

Reads NajAmjad's URLs + tokens from ``.env`` (NAJAMJAD_COP_URL/TOKEN, NAJAMJAD_THIEF_URL/TOKEN).
Two modes:
  --dry  : play ONE sub-game, print the K3 digest of that single agreed entry. Send it to NajAmjad;
           they must compute the SAME digest before we run the real 6.
  --full : play all 6 role-swap sub-games, write reports/bonus_game.json (the agreed format) and
           print the K3 digest. FILL the TODO_ student/repo fields before emailing.
Usage:  uv run python scripts/bonus_run.py --dry        (or)  --full
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from cosmos77_ex06.bonus import intergroup, intergroup_series
from cosmos77_ex06.bonus.remote import RemoteMoveSource
from cosmos77_ex06.shared.config import Config

# The exact strings BOTH groups put in sub_games[].cop_url / thief_url for OUR side (lock these).
OUR_COP_URL = "https://cosmos77-cop.fastmcp.app/mcp"
OUR_THIEF_URL = "https://cosmos77-thief.fastmcp.app/mcp"


def _env() -> dict[str, str]:
    """Load ``.env`` (KEY=VALUE lines) into a dict without extra deps."""
    out: dict[str, str] = {}
    for line in Path(".env").read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def _claim(wins: int) -> float:
    """Bonus claim: win 10 / lose 7 (no ties, barriers off), averaged over 6 sub-games."""
    return round((wins * 10 + (6 - wins) * 7) / 6, 4)


async def main(full: bool) -> None:
    env = _env()
    cfg = Config()
    teams = {"our": "COSMOS77", "their": "NajAmjad"}
    urls = {
        "our_cop": OUR_COP_URL,
        "our_thief": OUR_THIEF_URL,
        "their_cop": env["NAJAMJAD_COP_URL"],
        "their_thief": env["NAJAMJAD_THIEF_URL"],
    }
    their_cop = RemoteMoveSource(env["NAJAMJAD_COP_URL"], env["NAJAMJAD_COP_TOKEN"], timeout=25)
    their_thief = RemoteMoveSource(
        env["NAJAMJAD_THIEF_URL"], env["NAJAMJAD_THIEF_TOKEN"], timeout=25
    )

    if not full:
        sub = await intergroup.play_sub_game(cfg, 1, "thief", their_cop)
        entry = intergroup_series._entry(1, "thief", sub["winner"], teams, urls, cfg)  # noqa: SLF001
        print("DRY-RUN sub-game 1 entry:\n ", json.dumps(entry))
        print("DRY-RUN K3 digest (sha256 over [entry]):", intergroup.digest([entry]))
        print("=> send this entry + digest to NajAmjad; they must match it before the real 6.")
        return

    res = await intergroup_series.run_series(cfg, teams, urls, their_cop, their_thief)
    sg = res["sub_games"]
    our_wins = sum(1 for e in sg if (e["cop_team"] == "COSMOS77") == (e["outcome"] == "cop_wins"))
    their_wins = 6 - our_wins
    totals = {
        "COSMOS77": sum(
            e["cop_points"] if e["cop_team"] == "COSMOS77" else e["thief_points"] for e in sg
        ),
        "NajAmjad": sum(
            e["cop_points"] if e["cop_team"] == "NajAmjad" else e["thief_points"] for e in sg
        ),
    }
    report = {
        "report_type": "bonus_game",
        "groups": {"group_1": "NajAmjad", "group_2": "COSMOS77"},
        "github_repo_group_1": "TODO_NAJAMJAD_REPO",
        "github_repo_group_2": "https://github.com/AbdallahKhaldi/COSMOS77-ex06",
        "students_group_1": "TODO_NAJAMJAD_STUDENTS",
        "students_group_2": "TODO_OUR_STUDENTS",
        "mcp_url_group_1_cop": env["NAJAMJAD_COP_URL"],
        "mcp_url_group_1_thief": env["NAJAMJAD_THIEF_URL"],
        "mcp_url_group_2_cop": OUR_COP_URL,
        "mcp_url_group_2_thief": OUR_THIEF_URL,
        "sub_games": sg,
        "digest": res["digest"],
        "totals_by_group": totals,
        "bonus_claim": {"COSMOS77": _claim(our_wins), "NajAmjad": _claim(their_wins)},
        "mutual_agreement": True,
        "timezone": "Asia/Jerusalem",
    }
    Path("reports/bonus_game.json").write_text(json.dumps(report, indent=2) + "\n", "utf-8")
    print(f"6 sub-games played. totals={totals} | our wins={our_wins}/6")
    print("K3 digest:", res["digest"])
    print("wrote reports/bonus_game.json  —  FILL the three TODO_ fields, then email it.")


asyncio.run(main("--full" in sys.argv))
