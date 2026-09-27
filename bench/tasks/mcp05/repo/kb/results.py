"""Turning `search` tool results into titles."""

from __future__ import annotations

from typing import Any


def split_titles(result: Any) -> list[str]:
    """The `search` tool answers with one title per line; blank lines are ignored."""
    text = "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")
    return [line.strip() for line in text.splitlines() if line.strip()]
