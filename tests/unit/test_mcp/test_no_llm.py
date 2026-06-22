"""E3 guard: no LLM/genai/gemini/openai/anthropic import anywhere under mcp_servers/."""

from __future__ import annotations

from pathlib import Path

import cosmos77_ex06.mcp_servers as pkg

FORBIDDEN = ("genai", "gemini", "google.genai", "openai", "anthropic", "llm", "langchain")


def test_no_llm_imports_in_mcp_servers() -> None:
    """Grep every server source file for any LLM reference (Server/Client separation)."""
    root = Path(pkg.__file__).parent
    offenders: list[str] = []
    for src in root.glob("*.py"):
        text = src.read_text(encoding="utf-8").lower()
        for needle in FORBIDDEN:
            # only flag actual import lines, not prose in docstrings
            for line in text.splitlines():
                stripped = line.strip()
                if stripped.startswith(("import ", "from ")) and needle in stripped:
                    offenders.append(f"{src.name}: {line.strip()}")
    assert not offenders, f"LLM references found under mcp_servers/: {offenders}"
