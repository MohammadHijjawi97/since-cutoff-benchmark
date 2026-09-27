"""Inventory MCP server (2.x class, 1.x constructor settings: MCPServer(host=, port=))."""

from __future__ import annotations

import argparse

from mcp.server.mcpserver import MCPServer

from app import inventory


def build_server(host: str = "127.0.0.1", port: int = 8000) -> MCPServer:
    server = MCPServer("inventory", instructions="Stock levels and reservations for the warehouse.",
                       host=host, port=port)

    @server.tool()
    def stock(sku: str) -> int:
        """Units in stock for a SKU."""
        return inventory.stock_level(sku)

    @server.tool()
    def reserve(sku: str, quantity: int) -> int:
        """Reserve units of a SKU; returns the units left."""
        return inventory.reserve(sku, quantity)

    return server


def serve_http(host: str, port: int) -> None:
    build_server(host=host, port=port).run(transport="streamable-http")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m app.server")
    parser.add_argument("--http", action="store_true", help="serve remote agents over HTTP instead of stdio")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    if args.http:
        serve_http(args.host, args.port)
    else:
        build_server().run()


if __name__ == "__main__":
    main()
