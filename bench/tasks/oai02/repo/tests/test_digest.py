from app import digest
from tests.fakes import mock_openai

THREAD = (
    "Customer: every invoice PDF has been blank since Monday.\n"
    "Agent: cleared the render cache and re-sent the invoices; the customer confirmed they open."
)


def test_summarize_strips_the_reply():
    with mock_openai("  Blank invoice PDFs, fixed by clearing the render cache.  ") as seen:
        assert digest.summarize(THREAD) == "Blank invoice PDFs, fixed by clearing the render cache."
    assert len(seen) == 1
    assert seen[0]["model"] == digest.MODEL
    assert seen[0]["messages"][1] == {"role": "user", "content": THREAD}


def test_build_digest_asks_for_headline_then_summary():
    with mock_openai("Blank invoice PDFs.", "Fixed by clearing the render cache.") as seen:
        rows = digest.build_digest({"T-1042": THREAD})
    assert rows == [
        {"id": "T-1042", "headline": "Blank invoice PDFs", "summary": "Fixed by clearing the render cache."}
    ]
    assert [body["max_completion_tokens"] for body in seen] == [24, 200]
