"""Enforce the 150-line cap on every Python file under src/, tests/, scripts/.

This script is invoked by both pre-commit and CI. It exits non-zero (printing
the offenders) if any tracked Python file exceeds the cap. The cap is a
non-negotiable rule from CLAUDE.md §1.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from pathlib import Path

LINE_CAP = 150
SCAN_ROOTS = ("src", "tests", "scripts")


def iter_python_files(roots: Iterable[str]) -> Iterable[Path]:
    """Yield every `.py` file under each root, skipping caches."""
    for root in roots:
        base = Path(root)
        if not base.exists():
            continue
        for path in base.rglob("*.py"):
            if any(part.startswith(".") for part in path.parts):
                continue
            if "__pycache__" in path.parts:
                continue
            yield path


def count_lines(path: Path) -> int:
    """Return the number of newline-terminated lines in `path`."""
    with path.open("rb") as fh:
        return sum(1 for _ in fh)


def find_offenders(roots: Iterable[str], cap: int = LINE_CAP) -> list[tuple[Path, int]]:
    """Return every file whose line count exceeds `cap`."""
    offenders: list[tuple[Path, int]] = []
    for path in iter_python_files(roots):
        lines = count_lines(path)
        if lines > cap:
            offenders.append((path, lines))
    offenders.sort(key=lambda pair: pair[1], reverse=True)
    return offenders


def main() -> int:
    """CLI entry point — exits 0 when every file fits, 1 otherwise."""
    offenders = find_offenders(SCAN_ROOTS)
    if not offenders:
        print(f"OK: every Python file under {SCAN_ROOTS} is <= {LINE_CAP} lines.")
        return 0
    print(f"FAIL: {len(offenders)} file(s) exceed the {LINE_CAP}-line cap:")
    for path, lines in offenders:
        print(f"  {path} — {lines} lines (over by {lines - LINE_CAP})")
    return 1


if __name__ == "__main__":
    sys.exit(main())
