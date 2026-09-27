"""One-line summaries of incoming tickets for the on-call channel."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from app.prompts import SUMMARY_PROMPT
from app.tickets import Ticket, ticket_text


def summarize_ticket(chat: BaseChatModel, ticket: Ticket) -> str:
    messages = [SystemMessage(content=SUMMARY_PROMPT), HumanMessage(content=ticket_text(ticket))]
    reply = chat.invoke(messages, stop=["\n\n"])
    return str(reply.content).strip()
