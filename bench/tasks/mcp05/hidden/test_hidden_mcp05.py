"""mcp05: client over Streamable HTTP with a bearer token (mcp==2.2.0).

A real MCP server (the SDK's own Streamable HTTP app) runs under uvicorn on a free 127.0.0.1 port
inside the test's event loop (loopback only, allowed by --allow-hosts), behind an ASGI gate that
records every request's Authorization header and answers 401 without the right token."""

import socket
from contextlib import asynccontextmanager

import anyio
import pytest
import uvicorn

from kb.remote import search_remote

try:  # mcp>=2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # pragma: no cover - mcp<2 (lets the same test run at the cutoff version)
    from mcp.server.fastmcp import FastMCP as _Server

TOKEN = "kb-test-token-3f9a"
DOCS = ["Rotating API keys", "Rotating log files", "Onboarding checklist"]
PROXY_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def loopback_direct(monkeypatch):
    """The grader points HTTP(S)_PROXY at a dead port; loopback traffic must bypass it."""
    for var in PROXY_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost,::1")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost,::1")


def build_kb_server():
    server = _Server("kb")

    @server.tool()
    def search(query: str) -> str:
        """Titles containing the query, one per line."""
        return "\n".join(title for title in DOCS if query.lower() in title.lower())

    return server


class RequireBearer:
    """ASGI gate: records (method, Authorization) of every HTTP request; 401 unless the token matches."""

    def __init__(self, app, token):
        self.app = app
        self.token = token
        self.seen = []

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            auth = dict(scope["headers"]).get(b"authorization", b"").decode("latin-1")
            self.seen.append((scope["method"], auth))
            if auth != f"Bearer {self.token}":
                await send({"type": "http.response.start", "status": 401,
                            "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": b"missing or wrong bearer token"})
                return
        await self.app(scope, receive, send)


@asynccontextmanager
async def serving(app):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning", lifespan="on"))
    async with anyio.create_task_group() as tg:
        tg.start_soon(server.serve, [sock])
        with anyio.fail_after(15):
            while not server.started:
                await anyio.sleep(0.05)
        try:
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            server.should_exit = True
            server.force_exit = True


@pytest.mark.anyio
async def test_search_remote_sends_bearer_token_over_streamable_http(loopback_direct):
    gate = RequireBearer(build_kb_server().streamable_http_app(), TOKEN)
    with anyio.fail_after(60):
        async with serving(gate) as url:
            titles = await search_remote(url, TOKEN, "rotating")
            nothing = await search_remote(url, TOKEN, "payroll")
    assert titles == ["Rotating API keys", "Rotating log files"]
    assert nothing == []
    assert any(method == "POST" for method, _ in gate.seen), gate.seen
    assert all(auth == f"Bearer {TOKEN}" for _, auth in gate.seen), gate.seen
