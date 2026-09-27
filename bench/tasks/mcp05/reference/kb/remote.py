"""Searching the deployed knowledge-base server."""

from __future__ import annotations

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from kb.results import split_titles


async def search_remote(url: str, token: str, query: str) -> list[str]:
    # mcp>=2: headers/auth/timeouts go on an httpx2.AsyncClient passed as http_client; the
    # transport yields (read, write) without the session-id callback.
    headers = {"Authorization": f"Bearer {token}"}
    async with httpx2.AsyncClient(headers=headers, timeout=httpx2.Timeout(30.0, read=300.0)) as http:
        async with streamable_http_client(url, http_client=http) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("search", {"query": query})
    return split_titles(result)
