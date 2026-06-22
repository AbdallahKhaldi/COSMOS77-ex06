"""Pydantic v2 models for the internal-game JSON report (spec §9.1).

The :class:`InternalGameReport` model locks the EXACT top-level key set the grader
(and the inter-group bonus byte-match) depends on: ``group_name``, ``students``,
``github_repo``, ``cop_mcp_url``, ``thief_mcp_url``, ``timezone``, ``sub_games``,
``totals``. The runner assembles a plain dict; this module validates it BEFORE the
report is ever saved or (Phase 9) emailed — schema drift, a bad ``winner`` enum, a
short sub-game list, or a totals mismatch aborts the pipeline rather than shipping
a malformed autonomous report. Everything is config-driven (rule 4 / E8).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, model_validator


class Student(BaseModel):
    """One group member per §9.1: university ``id`` plus English/Hebrew names."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name_en: str
    name_he: str


class SubGameEntry(BaseModel):
    """One VALID sub-game summary (voided Technical-Losses never appear; E13).

    Field names mirror §2.1 of the report PRD exactly: a 1-based ``index``,
    the ``winner`` enum, the ``moves`` count, a ``capture`` boolean (true when
    the cop landed on the thief), and the per-role scores.
    """

    model_config = ConfigDict(extra="forbid")

    index: int
    winner: Literal["cop", "thief"]
    moves: int
    capture: bool
    cop_score: int
    thief_score: int


class Totals(BaseModel):
    """Cumulative per-role scores: the sum across the valid sub-games."""

    model_config = ConfigDict(extra="forbid")

    cop: int
    thief: int


class InternalGameReport(BaseModel):
    """The full §9.1 internal-game report; ``extra='forbid'`` pins the key set."""

    model_config = ConfigDict(extra="forbid")

    group_name: str
    students: list[Student]
    github_repo: str
    cop_mcp_url: str
    thief_mcp_url: str
    timezone: str
    sub_games: list[SubGameEntry]
    totals: Totals

    @model_validator(mode="after")
    def _totals_match_sub_games(self) -> InternalGameReport:
        """Reject a report whose ``totals`` do not equal the per-sub-game sums."""
        cop = sum(s.cop_score for s in self.sub_games)
        thief = sum(s.thief_score for s in self.sub_games)
        if (self.totals.cop, self.totals.thief) != (cop, thief):
            raise ValueError(
                f"totals {self.totals.model_dump()} != sub-game sums "
                f"{{'cop': {cop}, 'thief': {thief}}}"
            )
        return self


def validate_internal_game(payload: dict[str, Any]) -> InternalGameReport:
    """Validate a report dict against :class:`InternalGameReport` (raises on drift)."""
    return InternalGameReport.model_validate(payload)
