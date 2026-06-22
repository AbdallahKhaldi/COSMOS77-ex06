"""Pydantic v2 models for the ``bonus_game`` JSON report (E12, spec §9.2).

Mirrors the patterns in ``report/schema.py`` (which we must not edit): every model
sets ``extra='forbid'`` so the EXACT key set the inter-group byte-match depends on
is pinned — a stray key, a bad ``result`` enum, or a totals/claim drift aborts the
pipeline before a malformed report can be serialized or emailed. :class:`BonusGameReport`
locks the §9.2 top-level keys: ``report_type``, ``groups``, ``github_repo_group_1/2``,
the four ``mcp_url_*`` URLs, ``timezone``, ``students_group_1/2``, ``sub_games``,
``totals_by_group``, ``bonus_claim``, ``mutual_agreement``.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class BonusStudent(BaseModel):
    """One group member in the bonus report: university ``id`` plus a display ``name``."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str


class Groups(BaseModel):
    """The two group codes, orientation fixed at coordination time (§7-A)."""

    model_config = ConfigDict(extra="forbid")

    group_1: str
    group_2: str


class BonusSubGame(BaseModel):
    """One role-swapped sub-game (§9.2): which group was cop/thief + the scores.

    ``cop_group``/``thief_group`` are the literal ``group_1``/``group_2`` slots, NOT
    the codes, so the swap is unambiguous: index 1-3 have cop ``group_1``, index 4-6
    swap to cop ``group_2``. ``result`` is ``capture`` (cop landed on the thief) or
    ``survival`` (thief outlasted ``max_moves``).
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    cop_group: Literal["group_1", "group_2"]
    thief_group: Literal["group_1", "group_2"]
    result: Literal["capture", "survival"]
    moves: int
    cop_score: int
    thief_score: int


class BonusGameReport(BaseModel):
    """The full §9.2 ``bonus_game`` report; ``extra='forbid'`` pins the key set."""

    model_config = ConfigDict(extra="forbid")

    report_type: Literal["bonus_game"]
    groups: Groups
    github_repo_group_1: str
    github_repo_group_2: str
    mcp_url_group_1_cop: str
    mcp_url_group_1_thief: str
    mcp_url_group_2_cop: str
    mcp_url_group_2_thief: str
    timezone: str
    students_group_1: list[BonusStudent]
    students_group_2: list[BonusStudent]
    sub_games: list[BonusSubGame]
    totals_by_group: dict[str, int]
    bonus_claim: dict[str, int]
    mutual_agreement: bool

    @model_validator(mode="after")
    def _consistency(self) -> BonusGameReport:
        """Reject drift: totals/claim keys must be the two group codes; totals must sum."""
        codes = {self.groups.group_1, self.groups.group_2}
        for label, mapping in (
            ("totals_by_group", self.totals_by_group),
            ("bonus_claim", self.bonus_claim),
        ):
            if set(mapping) != codes:
                raise ValueError(f"{label} keys {set(mapping)} != group codes {codes}")
        slot = {"group_1": self.groups.group_1, "group_2": self.groups.group_2}
        expected = {self.groups.group_1: 0, self.groups.group_2: 0}
        for sg in self.sub_games:
            expected[slot[sg.cop_group]] += sg.cop_score
            expected[slot[sg.thief_group]] += sg.thief_score
        if expected != self.totals_by_group:
            raise ValueError(f"totals_by_group {self.totals_by_group} != sub-game sums {expected}")
        return self


def validate_bonus_game(payload: dict[str, Any]) -> BonusGameReport:
    """Validate a report dict against :class:`BonusGameReport` (raises on drift)."""
    return BonusGameReport.model_validate(payload)
