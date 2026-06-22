"""Meta-rule tests for the game package (CLAUDE.md Rules 1, 15, 16).

These lock the cross-cutting engineering rules the PRD enforces on ``game/``:
the per-file line cap (Rule 1, with the tighter PRD §11 budget for ``match.py``),
module/public-callable docstrings (Rule 15), and type-hinted public signatures
(Rule 16). They keep the game modules honest as Phase 2 evolves.
"""

from __future__ import annotations

import importlib
import inspect
from pathlib import Path

import pytest

_GAME_DIR = Path(__file__).resolve().parents[3] / "src" / "cosmos77_ex06" / "game"
_MODULES = ["board", "match", "moves", "rules", "state"]
# Rule 1 hard cap; PRD §11 sets a tighter per-file budget for match.py.
_LINE_CAP = 150
_PRD_BUDGET = {"match": 140}


def _module_path(name: str) -> Path:
    return _GAME_DIR / f"{name}.py"


@pytest.mark.parametrize("name", _MODULES)
def test_game_module_within_line_cap(name: str) -> None:
    path = _module_path(name)
    lines = path.read_text(encoding="utf-8").splitlines()
    cap = _PRD_BUDGET.get(name, _LINE_CAP)
    assert len(lines) <= cap, f"{name}.py is {len(lines)} lines (cap {cap})"


@pytest.mark.parametrize("name", _MODULES)
def test_game_module_has_module_docstring(name: str) -> None:
    mod = importlib.import_module(f"cosmos77_ex06.game.{name}")
    assert mod.__doc__ and mod.__doc__.strip()


@pytest.mark.parametrize("name", _MODULES)
def test_public_callables_are_documented_and_typed(name: str) -> None:
    mod = importlib.import_module(f"cosmos77_ex06.game.{name}")
    for attr, obj in vars(mod).items():
        if attr.startswith("_") or getattr(obj, "__module__", None) != mod.__name__:
            continue
        if inspect.isfunction(obj):
            assert obj.__doc__ and obj.__doc__.strip(), f"{name}.{attr} lacks a docstring"
            assert obj.__annotations__, f"{name}.{attr} lacks type hints"
        elif inspect.isclass(obj):
            assert obj.__doc__ and obj.__doc__.strip(), f"{name}.{attr} lacks a docstring"
