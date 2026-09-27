"""Support tickets as they come from the help desk export."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Ticket:
    id: int
    customer: str
    subject: str
    body: str


def ticket_text(ticket: Ticket) -> str:
    """The ticket as a model sees it: a header line, the subject, a blank line, then the body."""
    return f"Ticket #{ticket.id} from {ticket.customer}\nSubject: {ticket.subject.strip()}\n\n{ticket.body.strip()}"
