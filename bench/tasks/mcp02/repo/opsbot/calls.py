"""Calling tools on the ops server."""

from __future__ import annotations

from typing import Any

from mcp import ClientSession


class ToolCallFailed(Exception):
    """The server ran the tool and reported that the call failed."""

    def __init__(self, tool: str, message: str) -> None:
        super().__init__(f"{tool} failed: {message}")
        self.tool = tool
        self.message = message


async def run_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    raise NotImplementedError
