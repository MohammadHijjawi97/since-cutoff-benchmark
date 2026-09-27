import pytest

from app import server as srv

try:  # mcp>=2: first-class Client that can connect to a server object in memory
    from mcp import Client

    def connect(server):
        return Client(server)

    def is_error(result):
        return result.is_error
except ImportError:  # pragma: no cover - mcp<2 (lets the same test run at the cutoff version)
    from mcp.shared.memory import create_connected_server_and_client_session

    def connect(server):
        return create_connected_server_and_client_session(server)

    def is_error(result):
        return result.isError


@pytest.fixture
def anyio_backend():
    return "asyncio"


def text_of(result):
    return " ".join(getattr(block, "text", "") for block in result.content)


@pytest.mark.anyio
async def test_tools_roundtrip_and_errors():
    srv.NOTES.clear()
    async with connect(srv.build_server()) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        assert {"add_note", "word_count"} <= names

        saved = await client.call_tool("add_note", {"title": "t", "body": "one two  three"})
        assert not is_error(saved) and "saved t" in text_of(saved)
        assert srv.NOTES == {"t": "one two  three"}

        counted = await client.call_tool("word_count", {"title": "t"})
        assert not is_error(counted) and text_of(counted).strip() == "3"

        missing = await client.call_tool("word_count", {"title": "nope"})
        assert is_error(missing)
        assert "no such note" in text_of(missing)
