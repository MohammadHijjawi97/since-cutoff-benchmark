"""mcp04: serve over Streamable HTTP on a given host/port (mcp==2.2.0).

serve_http() runs in a daemon thread on a free 127.0.0.1 port (loopback only, allowed by
--allow-hosts); the test connects with the SDK's own Streamable HTTP client."""

import socket
import threading
import time

import anyio
import pytest
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client  # present in 1.28.1 and 2.2.0

from app import inventory
from app import server as srv

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


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_serving(port: int, timeout: float = 20.0) -> threading.Thread:
    errors: list[BaseException] = []

    def target():
        try:
            srv.serve_http("127.0.0.1", port)
        except BaseException as exc:  # noqa: BLE001 - reported to the test thread
            errors.append(exc)

    thread = threading.Thread(target=target, name="serve_http", daemon=True)
    thread.start()
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not thread.is_alive():
            if errors:
                raise errors[0]
            pytest.fail("serve_http() returned instead of serving until the process is stopped")
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.25):
                return thread
        except OSError:
            time.sleep(0.1)
    if errors:
        raise errors[0]
    pytest.fail(f"serve_http('127.0.0.1', {port}) is not listening on 127.0.0.1:{port}")


def text_of(result) -> str:
    return " ".join(getattr(block, "text", "") for block in result.content)


@pytest.mark.anyio
async def test_serves_streamable_http_on_requested_port(loopback_direct, monkeypatch):
    monkeypatch.setitem(inventory.STOCK, "KB-101", 7)
    port = free_port()
    thread = start_serving(port)
    url = f"http://127.0.0.1:{port}/mcp"
    with anyio.fail_after(30):
        async with streamable_http_client(url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                names = {tool.name for tool in (await session.list_tools()).tools}
                assert {"stock", "reserve"} <= names
                result = await session.call_tool("stock", {"sku": "KB-101"})
                assert text_of(result).strip() == "7"
                result = await session.call_tool("reserve", {"sku": "KB-101", "quantity": 2})
                assert text_of(result).strip() == "5"
    assert inventory.STOCK["KB-101"] == 5
    assert thread.is_alive(), "the server must keep serving after a client disconnects"
