"""Build + canonically serialize the ``bonus_game`` JSON report (E12, spec §9.2).

The make-or-break constraint of the inter-group bonus: BOTH groups must email a
**byte-identical** ``bonus_game`` JSON, or the grade is 0 for both. We guarantee
our side is deterministic by construction by reusing the SAME canonical serializer
the single-group report uses (:func:`cosmos77_ex06.report.output.canonical_json` —
``sort_keys=True``, ``ensure_ascii=False``, ``indent=2``). A partner codebase that
applies the same canonical rules to the same agreed value object emits the same
bytes (see ``tests/unit/test_bonus``: a dict built in a different key order
serializes identically). The pydantic :class:`BonusGameReport` (``extra='forbid'``)
pins the exact key set before anything is serialized or sent.
"""

from __future__ import annotations

from typing import Any

from cosmos77_ex06.bonus.schema import validate_bonus_game
from cosmos77_ex06.report.output import canonical_json
from cosmos77_ex06.shared.config import Config


def totals_by_group(sub_games: list[dict[str, Any]], group_1: str, group_2: str) -> dict[str, int]:
    """Sum each group's points across all sub-games (the cop + thief credits it owned).

    Each sub-game labels its cop/thief side with the slot ``"group_1"``/``"group_2"``;
    this maps each slot to the agreed group CODE (``group_1``/``group_2`` args) and sums
    ``cop_score`` to the cop-side group and ``thief_score`` to the thief-side group, so a
    group's total spans its 3 cop sub-games + its 3 thief sub-games (§3.2). The result is
    keyed by the codes so ``totals_by_group`` carries the agreed group identities.
    """
    slot = {"group_1": group_1, "group_2": group_2}
    totals = {group_1: 0, group_2: 0}
    for sg in sub_games:
        totals[slot[str(sg["cop_group"])]] += int(sg["cop_score"])
        totals[slot[str(sg["thief_group"])]] += int(sg["thief_score"])
    return totals


def bonus_claim(
    totals: dict[str, int], group_1: str, group_2: str, thresholds: dict[str, int]
) -> dict[str, int]:
    """Resolve each group's award from the series outcome (win/lose/tie; §3.3).

    The higher cumulative ``totals_by_group`` claims ``thresholds['win']``, the
    lower ``thresholds['lose']``, and an exact tie ``thresholds['tie']`` each. The
    thresholds come from the ``bonus.claim`` config block (never hardcoded; Rule 4).
    """
    win, lose, tie = thresholds["win"], thresholds["lose"], thresholds["tie"]
    t1, t2 = totals[group_1], totals[group_2]
    if t1 == t2:
        return {group_1: tie, group_2: tie}
    if t1 > t2:
        return {group_1: win, group_2: lose}
    return {group_1: lose, group_2: win}


def _group_names(config: Config) -> tuple[str, str]:
    """Return the agreed ``(group_1, group_2)`` orientation from the bonus config."""
    return str(config.get("bonus.group_1")), str(config.get("bonus.group_2"))


def build_report(
    config: Config,
    sub_games: list[dict[str, Any]],
    *,
    mutual_agreement: bool = True,
) -> dict[str, Any]:
    """Assemble + validate the §9.2 ``bonus_game`` report dict from config + results.

    Pulls the agreed metadata (group codes, repos, students, the four MCP URLs,
    timezone) from the ``bonus`` config block, computes ``totals_by_group`` and
    ``bonus_claim`` deterministically, validates against :class:`BonusGameReport`,
    and returns the plain dict ready for :func:`serialize`. ``sub_games`` is the
    ordered length-6 list from :mod:`cosmos77_ex06.bonus.series`.
    """
    g1, g2 = _group_names(config)
    totals = totals_by_group(sub_games, g1, g2)
    thresholds = {k: int(config.get(f"bonus.claim.{k}")) for k in ("win", "lose", "tie")}
    report = {
        "report_type": "bonus_game",
        "groups": {"group_1": g1, "group_2": g2},
        "github_repo_group_1": str(config.get("group.github_repo")),
        "github_repo_group_2": str(config.get("bonus.github_repo_group_2")),
        "mcp_url_group_1_cop": str(config.get("bonus.mcp.group_1_cop")),
        "mcp_url_group_1_thief": str(config.get("bonus.mcp.group_1_thief")),
        "mcp_url_group_2_cop": str(config.get("bonus.mcp.group_2_cop")),
        "mcp_url_group_2_thief": str(config.get("bonus.mcp.group_2_thief")),
        "timezone": str(config.get("report.timezone")),
        "students_group_1": _students(config.get("students", default=[])),
        "students_group_2": _students(config.get("bonus.students_group_2", default=[])),
        "sub_games": [dict(sg) for sg in sub_games],
        "totals_by_group": totals,
        "bonus_claim": bonus_claim(totals, g1, g2, thresholds),
        "mutual_agreement": bool(mutual_agreement),
    }
    validate_bonus_game(report)
    return report


def _students(roster: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Normalize a roster to an ordered list of ``{id, name}`` (agreed list order)."""
    out: list[dict[str, str]] = []
    for s in roster:
        name = str(s.get("name", s.get("name_en", "")))
        out.append({"id": str(s["id"]), "name": name})
    return out


def serialize(report: dict[str, Any]) -> str:
    """Serialize a ``bonus_game`` dict to canonical, byte-stable JSON (shared E7/E12).

    Delegates to :func:`cosmos77_ex06.report.output.canonical_json` — the SAME
    serializer the single-group report uses — so both groups emit identical bytes.
    """
    return canonical_json(report)


def build(config: Config, sub_games: list[dict[str, Any]], **kwargs: Any) -> str:
    """Build, validate, and serialize the ``bonus_game`` report in one call."""
    return serialize(build_report(config, sub_games, **kwargs))
