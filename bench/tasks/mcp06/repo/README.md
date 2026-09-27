# mcpcheck

Golden-output checks for MCP servers: each case calls one tool and compares the text it returns.

```toml
# cases.toml
[[case]]
tool = "add"
arguments = { a = 2, b = 3 }
expect = "5"
```

    mcpcheck cases.toml -- python -m my_server     # launches the server over stdio

Planned: checking a server object in-process, for server authors' own pytest suites.
