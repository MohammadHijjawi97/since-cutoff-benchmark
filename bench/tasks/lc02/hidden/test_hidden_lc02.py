from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from app.prompts import SUMMARY_PROMPT
from app.summary import summarize_ticket
from app.tickets import Ticket, ticket_text


class SpyChat(BaseChatModel):
    """A chat model that answers with a fixed reply and records every request it gets."""

    reply: str = "ok"
    calls: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "spy-chat"

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, run_manager=None,
                  **kwargs: Any) -> ChatResult:
        self.calls.append({"messages": list(messages), "stop": stop, "kwargs": kwargs})
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])


TICKET = Ticket(
    id=4812,
    customer="Acme GmbH",
    subject="Invoices page blank",
    body="Since this morning the invoices page shows nothing for all of our users.",
)


def test_returns_the_reply_as_stripped_str():
    chat = SpyChat(reply="  The invoices page is blank for all Acme GmbH users.  \n")
    out = summarize_ticket(chat, TICKET)
    assert type(out) is str
    assert out == "The invoices page is blank for all Acme GmbH users."


def test_one_request_with_system_then_user_message():
    chat = SpyChat()
    summarize_ticket(chat, TICKET)
    assert len(chat.calls) == 1
    messages = chat.calls[0]["messages"]
    assert [m.type for m in messages] == ["system", "human"]
    assert messages[0].content == SUMMARY_PROMPT
    assert messages[1].content == ticket_text(TICKET)


def test_generation_stops_at_first_blank_line():
    chat = SpyChat()
    summarize_ticket(chat, TICKET)
    stop = chat.calls[0]["stop"]
    assert stop is not None
    assert ([stop] if isinstance(stop, str) else list(stop)) == ["\n\n"]
