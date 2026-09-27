"""Checking a server object in-process (for server authors' pytest suites)."""

from __future__ import annotations

from typing import Any

from mcpcheck.cases import Case, Mismatch


async def check_server(server: Any, cases: list[Case]) -> list[Mismatch]:
    raise NotImplementedError
