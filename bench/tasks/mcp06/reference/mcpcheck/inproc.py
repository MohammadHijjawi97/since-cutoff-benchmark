"""Checking a server object in-process (for server authors' pytest suites)."""

from __future__ import annotations

from typing import Any

from mcp import Client

from mcpcheck.cases import Case, Mismatch, compare


async def check_server(server: Any, cases: list[Case]) -> list[Mismatch]:
    # mcp>=2: Client accepts a server object and connects to it in-process (no transport, no subprocess)
    mismatches: list[Mismatch] = []
    async with Client(server) as client:
        for case in cases:
            result = await client.call_tool(case.tool, case.arguments)
            mismatch = compare(case, result)
            if mismatch is not None:
                mismatches.append(mismatch)
    return mismatches
