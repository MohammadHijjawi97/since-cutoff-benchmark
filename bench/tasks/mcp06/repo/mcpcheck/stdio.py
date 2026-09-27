"""Checking a server launched as a subprocess over stdio."""

from __future__ import annotations

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from mcpcheck.cases import Case, Mismatch, compare


async def check_command(command: list[str], cases: list[Case]) -> list[Mismatch]:
    """Launch `command`, call every case's tool in order and return the mismatches."""
    program, *args = command
    mismatches: list[Mismatch] = []
    async with stdio_client(StdioServerParameters(command=program, args=args)) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            for case in cases:
                result = await session.call_tool(case.tool, case.arguments)
                mismatch = compare(case, result)
                if mismatch is not None:
                    mismatches.append(mismatch)
    return mismatches
