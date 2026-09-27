"""Stand-in for `claude -p ... --output-format stream-json` in the tests. No model, no network.

Behaviour comes from <this file>.mode.json (written by the test next to its own copy of this script):
  {"mcp_status": "connected"|"failed", "result": "success"|"auth"|"hang", "first": "stale"|"reference"}
It edits app/client.py in the working directory like an agent would, and prints stream-json events.
"""

import json
import os
import sys
import time
from pathlib import Path

args = sys.argv[1:]
if "--version" in args:
    print("2.1.283 (Claude Code)")
    sys.exit(0)

mode_file = Path(__file__).with_suffix(".mode.json")
mode = json.loads(mode_file.read_text()) if mode_file.exists() else {}
prompt = sys.stdin.read()


def val(flag):
    return args[args.index(flag) + 1] if flag in args else None


def emit(ev):
    sys.stdout.write(json.dumps(ev) + "\n")
    sys.stdout.flush()


mcp_arg = val("--mcp-config")
mcp = json.loads(Path(mcp_arg).read_text()) if os.path.exists(mcp_arg) else json.loads(mcp_arg)
servers = [{"name": n, "status": mode.get("mcp_status", "connected")} for n in mcp.get("mcpServers", {})]
key_present = any("CONTEXT7_API_KEY" in (s.get("env") or {}) for s in mcp.get("mcpServers", {}).values())
emit({"type": "system", "subtype": "init", "model": val("--model"), "claude_code_version": "2.1.283",
      "apiKeySource": "none", "mcp_servers": servers, "cwd": os.getcwd(), "permissionMode": val("--permission-mode")})
emit({"type": "system", "subtype": "fake_env", "env_names": sorted(os.environ), "mcp_key_present": key_present,
      "flags": [a for a in args if a.startswith("--")], "prompt_chars": len(prompt),
      "claude_md": Path("CLAUDE.md").read_text(encoding="utf-8")})

if mode.get("result") == "hang":
    time.sleep(120)

if mode.get("result") == "auth":
    emit({"type": "result", "subtype": "success", "is_error": True, "num_turns": 1, "total_cost_usd": 0,
          "result": "Invalid API key · Please run /login", "permission_denials": []})
    sys.exit(1)

n = 0


def tool(name, inp, result, is_error=False):
    global n
    n += 1
    emit({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": f"t{n}", "name": name, "input": inp}]}})
    emit({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": f"t{n}", "content": result,
                                                    "is_error": is_error}]}})


client = Path("app") / "client.py"
stale = "import toylib\n\n\ndef get(url):\n    return toylib.fetch(url, retries=3)\n"
ref = "import toylib\n\n\ndef get(url):\n    return toylib.fetch(url, max_retries=3)\n"
if servers:
    tool("mcp__context7__query-docs", {"libraryId": "/toy/toylib", "query": "retries"},
         [{"type": "text", "text": "fetch(url, *, max_retries=0)"}])
tool("Read", {"file_path": str(Path(".venv/Lib/site-packages/toylib/__init__.py").resolve())}, "def fetch(...)")
first = stale if mode.get("first", "stale") == "stale" else ref
client.write_text(first)
tool("Write", {"file_path": str(client.resolve()), "content": first}, "File created successfully")
tool("Bash", {"command": "pytest -q"}, "Exit code 1\n1 failed in 0.1s" if first == stale else "1 passed", first == stale)
if first == stale:
    client.write_text(ref)
    tool("Edit", {"file_path": str(client.resolve()), "old_string": "retries=3", "new_string": "max_retries=3"},
         "The file has been updated")
    tool("Bash", {"command": "pytest -q"}, "1 passed in 0.1s")
emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": 6, "duration_ms": 1200,
      "duration_api_ms": 800, "total_cost_usd": 0.25 if servers else 0.2,
      "usage": {"input_tokens": 5, "output_tokens": 300, "cache_creation_input_tokens": 1000,
                "cache_read_input_tokens": 5000}, "modelUsage": {}, "permission_denials": [], "result": "Done."})
