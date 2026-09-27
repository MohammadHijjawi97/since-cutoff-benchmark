"""Notes MCP server (renamed only, as the ModuleNotFoundError suggests)."""

from mcp.server.mcpserver import MCPServer

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
            raise ValueError("no such note")
        return len(NOTES[title].split())

    return server


if __name__ == "__main__":
    build_server().run()
