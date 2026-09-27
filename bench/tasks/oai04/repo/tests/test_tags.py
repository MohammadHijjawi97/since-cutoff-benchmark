from types import SimpleNamespace

from app.drafts import TAG_MODEL, Ticket, suggest_tag

TICKET = Ticket(id="T-88", subject="Charged twice", body="My card was charged twice for September.")


class FakeResponses:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(output_text=self.text)


def test_suggest_tag_normalises_the_answer():
    responses = FakeResponses(" Billing\n")
    assert suggest_tag(SimpleNamespace(responses=responses), TICKET) == "billing"
    assert responses.calls[0]["model"] == TAG_MODEL
    assert responses.calls[0]["store"] is False


def test_unknown_tag_becomes_other():
    assert suggest_tag(SimpleNamespace(responses=FakeResponses("urgent")), TICKET) == "other"
