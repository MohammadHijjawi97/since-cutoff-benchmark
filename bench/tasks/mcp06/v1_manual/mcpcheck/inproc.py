"""Checking a server object in-process (1.x wiring by hand: memory streams + the private low-level server)."""

from __future__ import annotations

from typing import Any

import anyio
from mcp import ClientSession
from mcp.shared.memory import create_client_server_memory_streams

from mcpcheck.cases import Case, Mismatch, compare


async def check_server(server: Any, cases: list[Case]) -> list[Mismatch]:
    lowlevel = server._mcp_server
    mismatches: list[Mismatch] = []
    async with create_client_server_memory_streams() as (client_streams, server_streams):
        async with anyio.create_task_group() as tg:
            tg.start_soon(
                lambda: lowlevel.run(server_streams[0], server_streams[1], lowlevel.create_initialization_options())
            )
            async with ClientSession(client_streams[0], client_streams[1]) as session:
                await session.initialize()
                for case in cases:
                    result = await session.call_tool(case.tool, case.arguments)
                    mismatch = compare(case, result)
                    if mismatch is not None:
                        mismatches.append(mismatch)
            tg.cancel_scope.cancel()
    return mismatches
