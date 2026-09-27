"""Golden cases and how a tool result is compared with them."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Case:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)
    expect: str = ""


@dataclass(frozen=True)
class Mismatch:
    case: Case
    got: str


def load_cases(path: str | Path) -> list[Case]:
    with open(path, "rb") as fh:
        data = tomllib.load(fh)
    return [Case(c["tool"], dict(c.get("arguments", {})), c["expect"]) for c in data.get("case", [])]


def result_text(result: Any) -> str:
    """The text blocks of a tool result, joined with newlines."""
    return "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")


def compare(case: Case, result: Any) -> Mismatch | None:
    got = result_text(result)
    return None if got.strip() == case.expect.strip() else Mismatch(case, got)
