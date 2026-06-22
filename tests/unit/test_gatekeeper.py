"""Tests for the Gatekeeper LLM meter + result ledger (CLAUDE.md rule 13)."""

from __future__ import annotations

import json
from pathlib import Path

from cosmos77_ex06.shared.gatekeeper import Gatekeeper


def test_record_writes_json(tmp_path: Path) -> None:
    gk = Gatekeeper(tmp_path)
    path = gk.record("subgame_1", {"winner": "cop", "moves": 7})
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["scenario"] == "subgame_1"
    assert data["winner"] == "cop"
    assert data["moves"] == 7


def test_record_merges_into_existing(tmp_path: Path) -> None:
    gk = Gatekeeper(tmp_path)
    gk.record("subgame_1", {"winner": "cop"})
    gk.record("subgame_1", {"moves": 12})
    data = gk.read("subgame_1")
    assert data["winner"] == "cop"
    assert data["moves"] == 12


def test_read_missing_returns_empty(tmp_path: Path) -> None:
    assert Gatekeeper(tmp_path).read("nope") == {}


def test_ledger_aggregates_all(tmp_path: Path) -> None:
    gk = Gatekeeper(tmp_path)
    gk.record("subgame_1", {"winner": "cop"})
    gk.record("subgame_2", {"winner": "thief"})
    ledger = gk.ledger()
    assert set(ledger) == {"subgame_1", "subgame_2"}
    assert ledger["subgame_2"]["winner"] == "thief"


def test_ledger_empty_when_no_dir(tmp_path: Path) -> None:
    assert Gatekeeper(tmp_path / "absent").ledger() == {}


def test_ledger_skips_corrupt_json(tmp_path: Path) -> None:
    gk = Gatekeeper(tmp_path)
    gk.record("good", {"x": 1})
    (tmp_path / "bad.json").write_text("{not valid json", encoding="utf-8")
    ledger = gk.ledger()
    assert "good" in ledger
    assert "bad" not in ledger


def test_scrub_redacts_google_key() -> None:
    text = "key=AIzaSyA1234567890abcdefghijklmnopqrstuvwxyz end"
    scrubbed = Gatekeeper.scrub(text)
    assert "AIza" not in scrubbed
    assert "[REDACTED]" in scrubbed


def test_scrub_redacts_bearer_token() -> None:
    assert "[REDACTED]" in Gatekeeper.scrub("Authorization: Bearer abc.def-123")


def test_scrub_leaves_clean_text() -> None:
    assert Gatekeeper.scrub("the cop captured the thief") == "the cop captured the thief"
