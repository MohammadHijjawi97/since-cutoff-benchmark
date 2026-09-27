# kb-assistant

Searches the team knowledge base through its MCP server (tool `search(query)`, one title per line).

    kb "rotating keys"                         # local dev server over stdio ($KB_SERVER, default `kb-mcp`)
    KB_URL=https://kb.internal/mcp KB_TOKEN=... kb "rotating keys"   # remote server
