"""Searching a local knowledge-base server launched over stdio (development setup)."""

from __future__ import annotations

import os
import shlex

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from kb.results import split_titles


def server_command() -> list[str]:
    return shlex.split(os.environ.get("KB_SERVER", "kb-mcp"))


async def search_local(query: str, command: list[str] | None = None) -> list[str]:
    program, *args = command or server_command()
    params = StdioServerParameters(command=program, args=args)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search", {"query": query})
    return split_titles(result)
