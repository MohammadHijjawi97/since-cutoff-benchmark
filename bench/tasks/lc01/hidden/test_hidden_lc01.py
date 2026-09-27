from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from pydantic import Field

from app.context import MAX_SOURCES, TRACE_TAG, build_context
from app.kb import KeywordRetriever


class SpyRetriever(BaseRetriever):
    """Returns fixed documents and records every lookup as LangChain runs it (query and run tags)."""

    docs: list[Document] = Field(default_factory=list)
    queries: list[str] = Field(default_factory=list)
    tags_seen: list[list[str]] = Field(default_factory=list)

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> list[Document]:
        self.queries.append(query)
        self.tags_seen.append(list(run_manager.tags))
        return list(self.docs)


def doc(source: str, text: str) -> Document:
    return Document(page_content=text, metadata={"source": source})


def test_entries_numbered_deduplicated_and_capped():
    retriever = SpyRetriever(
        docs=[
            doc("vpn.md", "  Install the WireGuard client.\n"),
            doc("faq.md", "Ask in #it-help."),
            doc("vpn.md", "A second chunk of the VPN note."),
            doc("expenses.md", "Submit receipts by the 5th."),
            doc("travel.md", "Book through the portal."),
        ]
    )
    out = build_context(retriever, "how do I connect to the vpn?")
    assert MAX_SOURCES == 3
    assert out == (
        "[1] vpn.md\nInstall the WireGuard client.\n\n"
        "[2] faq.md\nAsk in #it-help.\n\n"
        "[3] expenses.md\nSubmit receipts by the 5th."
    )


def test_one_lookup_with_the_question_and_the_trace_tag():
    retriever = SpyRetriever(docs=[doc("a.md", "x")])
    build_context(retriever, "reset my password")
    assert retriever.queries == ["reset my password"]
    assert TRACE_TAG in retriever.tags_seen[0]


def test_nothing_found_gives_empty_string():
    retriever = SpyRetriever()
    assert build_context(retriever, "kubernetes") == ""
    assert retriever.queries == ["kubernetes"]


def test_with_the_keyword_retriever():
    kb = KeywordRetriever(
        docs=[
            doc("printer.md", "The office printer is on floor 2."),
            doc("vpn.md", "VPN: import the WireGuard profile from the IT portal."),
            doc("expenses.md", "Expenses: use the finance portal."),
        ]
    )
    out = build_context(kb, "vpn profile from the portal")
    assert out == (
        "[1] vpn.md\nVPN: import the WireGuard profile from the IT portal.\n\n"
        "[2] expenses.md\nExpenses: use the finance portal.\n\n"
        "[3] printer.md\nThe office printer is on floor 2."
    )
