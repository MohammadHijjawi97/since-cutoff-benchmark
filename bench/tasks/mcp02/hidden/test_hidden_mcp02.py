"""mcp02: tool-call results (mcp==2.2.0). Runs in memory; no network, no subprocess."""

from contextlib import asynccontextmanager

import anyio
import pytest

from opsbot.calls import ToolCallFailed, run_tool

try:  # mcp>=2
    from mcp import Client
    from mcp.server.mcpserver import MCPServer as _Server
    from mcp.server.mcpserver.exceptions import ToolError

    @asynccontextmanager
    async def ops_session(server):
        async with Client(server) as client:
            yield client.session  # the same ClientSession type opsbot.connection yields
except ImportError:  # pragma: no cover - mcp<2 (lets the same test run at the cutoff version)
    from mcp.server.fastmcp import FastMCP as _Server
    from mcp.server.fastmcp.exceptions import ToolError
    from mcp.shared.memory import create_connected_server_and_client_session as ops_session


@pytest.fixture
def anyio_backend():
    return "asyncio"


def build_ops_server():
    server = _Server("ops")

    @server.tool()
    def status(service: str) -> dict[str, str]:
        """Structured status of a service."""
        return {"service": service, "state": "running", "version": "4.2.0"}

    @server.tool()
    def restart(service: str):
        """Plain-text output only (no return annotation, so no structured output)."""
        return f"restarting {service}\nqueued as job 17"

    @server.tool()
    def deploy(service: str, version: str) -> str:
        raise ToolError(f"{service} {version} is not in the registry")

    return server


@pytest.mark.anyio
async def test_structured_result_is_returned_as_is():
    with anyio.fail_after(30):
        async with ops_session(build_ops_server()) as session:
            value = await run_tool(session, "status", {"service": "api"})
    assert value == {"service": "api", "state": "running", "version": "4.2.0"}


@pytest.mark.anyio
async def test_text_result_is_joined_text():
    with anyio.fail_after(30):
        async with ops_session(build_ops_server()) as session:
            value = await run_tool(session, "restart", {"service": "worker"})
    assert value == "restarting worker\nqueued as job 17"


@pytest.mark.anyio
async def test_failed_call_raises_with_server_message():
    with anyio.fail_after(30):
        async with ops_session(build_ops_server()) as session:
            with pytest.raises(ToolCallFailed) as info:
                await run_tool(session, "deploy", {"service": "api", "version": "9.9.9"})
    assert info.value.tool == "deploy"
    assert "api 9.9.9 is not in the registry" in info.value.message
