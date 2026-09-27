"""One-line summaries of incoming tickets for the on-call channel."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.prompts import SUMMARY_PROMPT
from app.tickets import Ticket, ticket_text


def summarize_ticket(chat: BaseChatModel, ticket: Ticket) -> str:
    raise NotImplementedError
