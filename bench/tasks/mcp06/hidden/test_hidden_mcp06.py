"""mcp06: golden cases against a server object in memory (mcp==2.2.0). No network, no subprocess."""

import anyio
import pytest

from mcpcheck.cases import Case, Mismatch
from mcpcheck.inproc import check_server

try:  # mcp>=2
    from mcp.server.mcpserver import Context
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # pragma: no cover - mcp<2 (lets the same test run at the cutoff version)
    from mcp.server.fastmcp import Context
    from mcp.server.fastmcp import FastMCP as _Server

CALLS: list[str] = []


@pytest.fixture
def anyio_backend():
    return "asyncio"


def build_server():
    server = _Server("golden")

    @server.tool()
    def add(a: int, b: int) -> int:
        CALLS.append("add")
        return a + b

    @server.tool()
    def greet(name: str) -> str:
        CALLS.append("greet")
        return f"Hello, {name}!"

    @server.tool()
    def request_marker(ctx: Context) -> str:
        """Tools that use the request context only work when called through a client session."""
        CALLS.append("request_marker")
        return "in-request" if ctx.request_id else "no-request"

    return server


@pytest.mark.anyio
async def test_cases_run_in_memory_in_order():
    CALLS.clear()
    cases = [
        Case("add", {"a": 2, "b": 3}, "5"),
        Case("greet", {"name": "Ada"}, "Hello, Ada!"),
        Case("greet", {"name": "Bob"}, "Hi Bob"),
        Case("request_marker", {}, "in-request"),
    ]
    with anyio.fail_after(30):
        mismatches = await check_server(build_server(), cases)
    assert mismatches == [Mismatch(cases[2], "Hello, Bob!")]
    assert CALLS == ["add", "greet", "greet", "request_marker"]


@pytest.mark.anyio
async def test_all_cases_pass():
    CALLS.clear()
    cases = [Case("add", {"a": 40, "b": 2}, "42")]
    with anyio.fail_after(30):
        assert await check_server(build_server(), cases) == []
    assert CALLS == ["add"]
