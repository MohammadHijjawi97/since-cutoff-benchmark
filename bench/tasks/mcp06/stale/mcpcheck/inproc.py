"""Checking a server object in-process (1.x-era code)."""

from __future__ import annotations

from typing import Any

from mcp.shared.memory import create_connected_server_and_client_session

from mcpcheck.cases import Case, Mismatch, compare


async def check_server(server: Any, cases: list[Case]) -> list[Mismatch]:
    mismatches: list[Mismatch] = []
    async with create_connected_server_and_client_session(server) as session:
        for case in cases:
            result = await session.call_tool(case.tool, case.arguments)
            mismatch = compare(case, result)
            if mismatch is not None:
                mismatches.append(mismatch)
    return mismatches
