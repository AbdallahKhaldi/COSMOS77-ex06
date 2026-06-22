"""No-coordinate channel guard for outgoing agent messages (E4, PRD §7.5/§10).

The graded claim is that the two agents talk in FREE natural language, never a
rigid numeric protocol. This guard scans every OUTGOING message for
coordinate-shaped tokens (``3,4`` pairs, ``row 3``, ``col 4``, bracketed /
parenthesized pairs) and reports a boolean flag the transcript records as
``coord_flagged``. The regexes are config-driven (``nl_guard.coord_patterns``)
so nothing is hardcoded (Rule 4); a built-in fallback keeps tiny test configs
working. No LLM lives here — it is a pure text check (E3).
"""

from __future__ import annotations

import re

from cosmos77_ex06.shared.config import Config

#: Fallback patterns when ``nl_guard.coord_patterns`` is absent from config.
_DEFAULT_PATTERNS: tuple[str, ...] = (
    r"\d+\s*[,;]\s*\d+",
    r"\brow\s*\d",
    r"\bcol\s*\d",
    r"\[\s*\d+\s*,\s*\d+\s*\]",
    r"\(\s*\d+\s*,\s*\d+\s*\)",
)


class CoordinateGuard:
    """Compiles the config coordinate patterns and flags numeric leaks in prose."""

    def __init__(self, config: Config) -> None:
        patterns = config.get("nl_guard.coord_patterns", default=list(_DEFAULT_PATTERNS))
        self._regexes = [re.compile(p, re.IGNORECASE) for p in patterns]

    def is_flagged(self, message: str) -> bool:
        """Return ``True`` if ``message`` contains a coordinate-shaped token (E4 violation)."""
        text = message or ""
        return any(rx.search(text) for rx in self._regexes)
