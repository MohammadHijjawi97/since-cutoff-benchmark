"""Calling tools on the ops server (1.x-era code)."""

from __future__ import annotations

from typing import Any

from mcp import ClientSession


class ToolCallFailed(Exception):
    """The server ran the tool and reported that the call failed."""

    def __init__(self, tool: str, message: str) -> None:
        super().__init__(f"{tool} failed: {message}")
        self.tool = tool
        self.message = message


def _text(result: Any) -> str:
    return "\n".join(block.text for block in result.content if getattr(block, "type", None) == "text")


async def run_tool(session: ClientSession, name: str, arguments: dict[str, Any]) -> Any:
    result = await session.call_tool(name, arguments)
    if result.isError:
        raise ToolCallFailed(name, _text(result))
    if result.structuredContent is not None:
        return result.structuredContent
    return _text(result)
