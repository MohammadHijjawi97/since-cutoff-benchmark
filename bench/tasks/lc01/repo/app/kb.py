"""The team knowledge base: markdown notes loaded as LangChain documents, plus a keyword retriever."""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

_WORD = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def load_notes(folder: str | Path) -> list[Document]:
    """One document per markdown file; metadata["source"] is the file name."""
    return [
        Document(page_content=path.read_text(encoding="utf-8"), metadata={"source": path.name})
        for path in sorted(Path(folder).glob("*.md"))
    ]


def rank(docs: list[Document], query: str, k: int) -> list[Document]:
    """The k documents sharing the most words with the query (ties keep the original order)."""
    wanted = tokens(query)
    scored = [(len(wanted & tokens(doc.page_content)), i, doc) for i, doc in enumerate(docs)]
    hits = sorted((item for item in scored if item[0] > 0), key=lambda item: (-item[0], item[1]))
    return [doc for _, _, doc in hits[:k]]


class KeywordRetriever(BaseRetriever):
    """Keyword-overlap retriever used in development and tests."""

    docs: list[Document]
    k: int = 4

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        return rank(self.docs, query, self.k)
