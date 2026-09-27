"""Runtime probe for the dropped task mcp03 (run with an mcp 1.28.1 or 2.2.0 venv's python; offline, in memory).

Premise tested: "Context.info(message, **extra) became Context.info(data, *, logger_name=None) in mcp 2.x, so
cutoff-era server code that logs to the client breaks". Each calling form runs inside a tool, called through an
in-memory client; the probe prints whether the call errored, what the client received and the tool's text.

    C:/b/venvs/mcp-1.28.1/Scripts/python bench/dropped/mcp03/probe.py
    C:/b/venvs/mcp-2.2.0/Scripts/python bench/dropped/mcp03/probe.py

A second part (2.2.0 only) checks whether log delivery changed for 1.x-style clients (ClientSession + initialize()).
"""

import warnings
from importlib.metadata import version

import anyio

warnings.simplefilter("ignore")  # 2.2.0 marks every ctx.log/info call with MCPDeprecationWarning (SEP-2577)

try:  # mcp>=2
    from mcp import Client, ClientSession
    from mcp.server.mcpserver import Context
    from mcp.server.mcpserver import MCPServer as Server
    from mcp.shared.memory import create_client_server_memory_streams

    V2 = True

    def connect(server, callback):
        return Client(server, logging_callback=callback, log_level="debug")  # opt in so delivery is not the variable

    def is_error(result):
        return result.is_error
except ImportError:
    from mcp.server.fastmcp import Context
    from mcp.server.fastmcp import FastMCP as Server
    from mcp.shared.memory import create_connected_server_and_client_session

    V2 = False

    def connect(server, callback):
        return create_connected_server_and_client_session(server, logging_callback=callback)

    def is_error(result):
        return result.isError


FORMS = {
    "ctx.info('hello')": lambda ctx: ctx.info("hello"),
    "ctx.info({...dict...})": lambda ctx: ctx.info({"msg": "hello", "rows": 3}),
    "ctx.info('hello', logger_name='importer')": lambda ctx: ctx.info("hello", logger_name="importer"),
    "ctx.info('hello', extra={'rows': 3})": lambda ctx: ctx.info("hello", extra={"rows": 3}),
    "ctx.info('hello', rows=3)": lambda ctx: ctx.info("hello", rows=3),
    "ctx.info(message='hello')": lambda ctx: ctx.info(message="hello"),
    "ctx.info(data='hello')": lambda ctx: ctx.info(data="hello"),
    "ctx.log(level='info', message='hello')": lambda ctx: ctx.log(level="info", message="hello"),
    "ctx.log('info', 'hello')": lambda ctx: ctx.log("info", "hello"),
}


def make_tool(form):
    async def tool(ctx: Context) -> str:
        await form(ctx)
        return "ok"

    return tool


async def calling_forms():
    server = Server("probe")
    for i, form in enumerate(FORMS.values()):
        server.add_tool(make_tool(form), name=f"t{i}")
    print(f"mcp {version('mcp')}")
    for i, label in enumerate(FORMS):
        received = []

        async def callback(params):
            received.append(params.data)

        async with connect(server, callback) as client:
            result = await client.call_tool(f"t{i}", {})
        text = " ".join(getattr(block, "text", "") for block in result.content)
        print(f"  {label:44s} error={is_error(result)!s:5s} client got={received} text={text[:95]!r}")


async def delivery_to_v1_style_client():
    server = Server("logs")

    @server.tool()
    async def work(ctx: Context) -> str:
        await ctx.info("step 1")
        return "ok"

    async def via_session():
        got = []

        async def callback(params):
            got.append(params.data)

        low = server._lowlevel_server
        async with create_client_server_memory_streams() as (client_streams, server_streams):
            async with anyio.create_task_group() as tg:
                tg.start_soon(lambda: low.run(server_streams[0], server_streams[1], low.create_initialization_options()))
                async with ClientSession(client_streams[0], client_streams[1], logging_callback=callback) as session:
                    await session.initialize()
                    await session.call_tool("work", {})
                tg.cancel_scope.cancel()
        return got

    async def via_client(**kwargs):
        got = []

        async def callback(params):
            got.append(params.data)

        async with Client(server, logging_callback=callback, **kwargs) as client:
            await client.call_tool("work", {})
        return got

    print("  log delivery at 2.2.0:")
    print(f"    ClientSession + initialize() (1.x-style client), logging_callback only: {await via_session()}")
    print(f"    Client(server, logging_callback=cb)                (new API, mode='auto'): {await via_client()}")
    print(f"    Client(server, logging_callback=cb, mode='legacy'):                      {await via_client(mode='legacy')}")
    print(f"    Client(server, logging_callback=cb, log_level='info'):                   {await via_client(log_level='info')}")


async def main():
    await calling_forms()
    if V2:
        await delivery_to_v1_style_client()


if __name__ == "__main__":
    anyio.run(main)
