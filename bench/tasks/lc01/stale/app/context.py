"""Builds the context block that goes into the answer prompt (langchain-core < 1.0 idiom)."""

from __future__ import annotations

from langchain_core.retrievers import BaseRetriever

MAX_SOURCES = 3
TRACE_TAG = "kb-context"


def build_context(retriever: BaseRetriever, question: str) -> str:
    docs = retriever.get_relevant_documents(question, tags=[TRACE_TAG])
    entries: list[str] = []
    seen: set[str] = set()
    for doc in docs:
        source = doc.metadata.get("source")
        if source in seen:
            continue
        seen.add(source)
        entries.append(f"[{len(entries) + 1}] {source}\n{doc.page_content.strip()}")
        if len(entries) == MAX_SOURCES:
            break
    return "\n\n".join(entries)
