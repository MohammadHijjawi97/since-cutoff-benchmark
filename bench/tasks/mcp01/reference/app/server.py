"""Notes MCP server."""

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

NOTES: dict[str, str] = {}


def build_server() -> MCPServer:
    server = MCPServer("notes")

    @server.tool()
    def add_note(title: str, body: str) -> str:
        NOTES[title] = body
        return f"saved {title}"

    @server.tool()
    def word_count(title: str) -> int:
        if title not in NOTES:
            # mcp>=2 withholds the text of unexpected exceptions; ToolError is shown to the model
            raise ToolError("no such note")
        return len(NOTES[title].split())

    return server


if __name__ == "__main__":
    build_server().run()
