"""Reply drafts for the support inbox, written with the OpenAI Responses API."""

from __future__ import annotations

from dataclasses import dataclass

from openai import OpenAI

DRAFT_MODEL = "gpt-5.5"
TAG_MODEL = "gpt-5.5-mini"
MAX_DRAFT_TOKENS = 400

STYLE_GUIDE = (
    "You write e-mail replies for the Northwind Cloud support team. Be friendly and concrete, "
    "use at most three short paragraphs, and never promise refunds or credits."
)
TAGS = ("billing", "outage", "account", "feature-request", "other")


@dataclass(frozen=True)
class Ticket:
    id: str
    subject: str
    body: str


@dataclass(frozen=True)
class Draft:
    ticket_id: str
    text: str
    truncated: bool


def suggest_tag(client: OpenAI, ticket: Ticket) -> str:
    """One tag from TAGS for the ticket ("other" when the model answers anything else)."""
    response = client.responses.create(
        model=TAG_MODEL,
        instructions="Classify the support ticket. Answer with exactly one word from: " + ", ".join(TAGS) + ".",
        input=f"{ticket.subject}\n\n{ticket.body}",
        max_output_tokens=16,
        store=False,
    )
    tag = response.output_text.strip().lower()
    return tag if tag in TAGS else "other"


def draft_reply(client: OpenAI, ticket: Ticket) -> Draft:
    response = client.responses.create(
        model=DRAFT_MODEL,
        instructions=STYLE_GUIDE,
        input=f"Subject: {ticket.subject}\n\n{ticket.body}",
        max_output_tokens=MAX_DRAFT_TOKENS,
        store=False,
        metadata={"ticket_id": ticket.id},
    )
    truncated = response.status == "incomplete" and (
        getattr(response.incomplete_details, "reason", None) == "max_output_tokens"
    )
    return Draft(ticket_id=ticket.id, text=response.output_text.strip(), truncated=truncated)
