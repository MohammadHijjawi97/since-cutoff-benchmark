"""`opsbot <tool> key=value ...`: call one tool on the ops server and print the result."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import anyio

from opsbot.calls import ToolCallFailed, run_tool
from opsbot.connection import open_session, tool_names


def parse_pairs(pairs: list[str]) -> dict[str, str]:
    """["service=api", "version=4.3.0"] -> {"service": "api", "version": "4.3.0"}"""
    arguments: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise ValueError(f"expected key=value, got {pair!r}")
        arguments[key] = value
    return arguments


def render(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2, sort_keys=True)
    return str(value)


async def _main(ns: argparse.Namespace) -> int:
    async with open_session() as session:
        if ns.tool == "tools":
            print("\n".join(await tool_names(session)))
            return 0
        try:
            value = await run_tool(session, ns.tool, parse_pairs(ns.pairs))
        except ToolCallFailed as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
    print(render(value))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="opsbot")
    parser.add_argument("tool", help="tool name, or `tools` to list them")
    parser.add_argument("pairs", nargs="*", metavar="key=value")
    ns = parser.parse_args(argv)
    return anyio.run(_main, ns)


if __name__ == "__main__":
    sys.exit(main())
