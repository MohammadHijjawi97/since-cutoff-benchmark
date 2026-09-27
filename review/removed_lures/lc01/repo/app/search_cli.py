"""`python -m app.search_cli <notes-folder> <query...>`: print the best matching notes."""

from __future__ import annotations

import sys

from app.kb import KeywordRetriever, load_notes


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) < 2:
        print("usage: python -m app.search_cli <notes-folder> <query...>", file=sys.stderr)
        return 2
    retriever = KeywordRetriever(docs=load_notes(args[0]), k=5)
    for doc in retriever.get_relevant_documents(" ".join(args[1:])):
        first_line = doc.page_content.strip().splitlines()[0]
        print(f"{doc.metadata['source']}: {first_line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
