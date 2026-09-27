"""`kb <query>`: print matching knowledge-base titles."""

from __future__ import annotations

import os
import sys

import anyio

from kb.local import search_local
from kb.remote import search_remote


async def _search(query: str) -> list[str]:
    url = os.environ.get("KB_URL")
    if url:
        return await search_remote(url, os.environ["KB_TOKEN"], query)
    return await search_local(query)


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args:
        print("usage: kb <query>", file=sys.stderr)
        return 2
    for title in anyio.run(_search, " ".join(args)):
        print(title)
    return 0


if __name__ == "__main__":
    sys.exit(main())
