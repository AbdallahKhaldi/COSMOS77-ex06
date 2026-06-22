"""Version constant + config-version validation (CLAUDE.md rule 10).

The single source of truth for the project version. ``config/config.yaml``
carries a matching ``"version"`` and is checked against ``VERSION`` at load time,
so a stale config fails fast instead of silently driving the pipeline wrong.
"""

from __future__ import annotations

from typing import Final

VERSION: Final[str] = "1.00"


def validate_config_version(cfg_version: str) -> None:
    """Raise ``ValueError`` when ``cfg_version`` does not match ``VERSION`` exactly.

    HW6 pins the whole assignment to 1.00, so any drift is a mistake, not an
    upgrade — we reject it loudly at config-load time.
    """
    if cfg_version != VERSION:
        raise ValueError(
            f"config version {cfg_version!r} does not match project version {VERSION!r}"
        )
