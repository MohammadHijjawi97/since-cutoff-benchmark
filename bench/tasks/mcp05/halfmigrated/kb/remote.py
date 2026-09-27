"""Searching the deployed knowledge-base server (renamed only, as the ImportError suggests)."""

from __future__ import annotations

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from kb.results import split_titles


async def search_remote(url: str, token: str, query: str) -> list[str]:
    headers = {"Authorization": f"Bearer {token}"}
    async with streamable_http_client(url, headers=headers) as (read, write, _get_session_id):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool("search", {"query": query})
    return split_titles(result)
