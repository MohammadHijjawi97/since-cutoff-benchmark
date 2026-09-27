from pathlib import Path

from app.kb import KeywordRetriever, load_notes, rank, tokens

NOTES = Path(__file__).parent / "data" / "notes"


def test_tokens_are_lower_case_words():
    assert tokens("VPN: WireGuard, v2!") == {"vpn", "wireguard", "v2"}


def test_load_notes_sets_source():
    docs = load_notes(NOTES)
    assert [d.metadata["source"] for d in docs] == ["expenses.md", "printer.md", "vpn.md"]
    assert docs[2].page_content.startswith("# VPN access")


def test_rank_orders_by_overlap_and_drops_misses():
    docs = load_notes(NOTES)
    top = rank(docs, "vpn for the staging database", k=2)
    assert [d.metadata["source"] for d in top] == ["vpn.md", "printer.md"]
    assert rank(docs, "kubernetes", k=3) == []


def test_retriever_defaults():
    retriever = KeywordRetriever(docs=load_notes(NOTES))
    assert retriever.k == 4 and len(retriever.docs) == 3
