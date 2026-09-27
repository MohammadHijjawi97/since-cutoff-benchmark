from types import SimpleNamespace

from app import chat


def test_build_messages_keeps_history_in_order():
    messages = chat.build_messages("And on Sundays?", [("Opening hours?", "9 to 5 on weekdays.")])
    assert [m["role"] for m in messages] == ["system", "user", "assistant", "user"]
    assert messages[-1] == {"role": "user", "content": "And on Sundays?"}


class FakeCompletions:
    def __init__(self, deltas):
        self.deltas = deltas
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return iter(
            SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=d))]) for d in self.deltas
        )


def test_iter_answer_yields_the_text_deltas():
    completions = FakeCompletions(["Reset ", None, "your password", ""])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    assert list(chat.iter_answer(client, "How do I log in?")) == ["Reset ", "your password"]
    assert completions.calls[0]["stream"] is True
    assert completions.calls[0]["model"] == chat.MODEL
