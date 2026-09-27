"""Connection to the ops MCP server, launched as a subprocess over stdio."""

from __future__ import annotations

import os
import shlex
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_SERVER = "ops-mcp"


def server_command() -> list[str]:
    """The server command line from $OPSBOT_SERVER (default: `ops-mcp`)."""
    return shlex.split(os.environ.get("OPSBOT_SERVER", DEFAULT_SERVER))


@asynccontextmanager
async def open_session(command: list[str] | None = None) -> AsyncIterator[ClientSession]:
    """Start the server and yield an initialized client session."""
    program, *args = command or server_command()
    params = StdioServerParameters(command=program, args=args)
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


async def tool_names(session: ClientSession) -> list[str]:
    """Names of the tools the server offers, sorted."""
    listing = await session.list_tools()
    return sorted(tool.name for tool in listing.tools)
