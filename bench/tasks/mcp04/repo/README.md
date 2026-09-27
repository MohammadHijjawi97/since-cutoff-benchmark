# inventory-mcp

MCP server for warehouse stock. Tools: `stock(sku)`, `reserve(sku, quantity)`.

    python -m app.server            # stdio (Claude Desktop, local agents)
    python -m app.server --http     # remote agents (not implemented yet)
