"""Notes MCP server."""

NOTES: dict[str, str] = {}


def build_server():
    raise NotImplementedError


if __name__ == "__main__":
    build_server().run()
