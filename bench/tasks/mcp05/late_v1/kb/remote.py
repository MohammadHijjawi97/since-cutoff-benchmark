"""Searching the deployed knowledge-base server (the non-deprecated 1.2x API: httpx client, 3-tuple)."""

from __future__ import annotations

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from kb.results import split_titles


async def search_remote(url: str, token: str, query: str) -> list[str]:
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient(headers=headers, timeout=httpx.Timeout(30.0, read=300.0)) as http:
        async with streamable_http_client(url, http_client=http) as (read, write, _get_session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("search", {"query": query})
    return split_titles(result)
