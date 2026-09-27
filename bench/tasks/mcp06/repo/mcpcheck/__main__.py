"""`mcpcheck CASES.toml -- COMMAND...`: run golden cases against a server launched over stdio."""

from __future__ import annotations

import sys

import anyio

from mcpcheck.cases import load_cases
from mcpcheck.stdio import check_command


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--" not in args or args.index("--") != 1 or len(args) < 3:
        print("usage: mcpcheck CASES.toml -- COMMAND [ARGS...]", file=sys.stderr)
        return 2
    cases = load_cases(args[0])
    mismatches = anyio.run(check_command, args[2:], cases)
    for m in mismatches:
        print(f"FAIL {m.case.tool}({m.case.arguments}): expected {m.case.expect!r}, got {m.got!r}")
    print(f"{len(cases) - len(mismatches)}/{len(cases)} cases passed")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
