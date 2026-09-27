# opsbot

Small chat-ops helper. It launches our ops MCP server (`ops-mcp`, stdio) and calls its tools:

    opsbot status service=api
    opsbot restart service=worker
    opsbot deploy service=api version=4.3.0

Set `OPSBOT_SERVER` to override the server command (default: `ops-mcp`).
