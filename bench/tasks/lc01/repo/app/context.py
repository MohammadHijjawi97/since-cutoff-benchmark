"""Builds the context block that goes into the answer prompt."""

from __future__ import annotations

from langchain_core.retrievers import BaseRetriever

MAX_SOURCES = 3
TRACE_TAG = "kb-context"


def build_context(retriever: BaseRetriever, question: str) -> str:
    raise NotImplementedError
