"""Scan study artifacts for secrets before anything is published: python -m bench.secretscan <dir>...

Looks for credential shapes (Anthropic, OpenAI, Hugging Face, GitHub, AWS, Slack, Google, JWTs,
private keys, bearer headers) and for local identity (the maintainer's email address, the
Windows user folder). Prints one line per finding (file, line, pattern, a masked excerpt) and
exits 1 when anything is found, so a publish step can refuse to go on.
"""

from __future__ import annotations

import re
import sys
from collections.abc import Iterable
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "anthropic key": re.compile(r"sk-ant-[A-Za-z0-9_\-]{20,}"),
    "openai key": re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_\-]{32,}"),
    "hugging face token": re.compile(r"\bhf_[A-Za-z0-9]{30,}"),
    "github token": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{60,})"),
    "aws access key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "slack token": re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    "google api key": re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    "context7 key": re.compile(r"\bctx7sk[-_][A-Za-z0-9_\-]{16,}"),
    "jwt": re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "bearer header": re.compile(r"(?i)authorization[\"']?\s*[:=]\s*[\"']?bearer\s+[A-Za-z0-9._\-]{20,}"),
    "oauth token env": re.compile(r"CLAUDE_CODE_OAUTH_TOKEN\s*=\s*[\"']?[A-Za-z0-9._\-]{20,}"),
}
IDENTITY: dict[str, re.Pattern[str]] = {
    "email address": re.compile(r"mohammad\.hijjawi1997@gmail\.com", re.I),
}
TEXT_SUFFIXES = {".jsonl", ".json", ".log", ".md", ".txt", ".diff", ".py", ".toml", ".xml", ".csv", ".cfg"}


def mask(text: str) -> str:
    return text[:6] + "…" + text[-3:] if len(text) > 12 else "…"


def scan_file(path: Path) -> Iterable[tuple[int, str, str]]:
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for number, line in enumerate(lines, 1):
        for name, pattern in {**PATTERNS, **IDENTITY}.items():
            for m in pattern.finditer(line):
                yield number, name, mask(m.group(0))


def scan(roots: list[Path]) -> list[str]:
    found = []
    for root in roots:
        files = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for path in files:
            if path.suffix.lower() not in TEXT_SUFFIXES or ".venv" in path.parts or "site-packages" in path.parts:
                continue
            for number, name, excerpt in scan_file(path):
                found.append(f"{path}:{number}: {name}: {excerpt}")
    return found


def main(argv: list[str] | None = None) -> int:
    roots = [Path(a) for a in (argv if argv is not None else sys.argv[1:])]
    if not roots:
        print(__doc__)
        return 2
    found = scan(roots)
    for line in found:
        print(line)
    print(f"{len(found)} finding(s) in {', '.join(map(str, roots))}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
