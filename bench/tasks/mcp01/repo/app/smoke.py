"""`python -m app.smoke`: start the notes server over stdio and print the tools it offers."""

import sys

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def list_tool_names() -> list[str]:
    params = StdioServerParameters(command=sys.executable, args=["-m", "app.server"])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listing = await session.list_tools()
    return sorted(tool.name for tool in listing.tools)


if __name__ == "__main__":
    print("\n".join(anyio.run(list_tool_names)))
