"""Short ticket summaries for the weekly support report."""

from anthropic import Anthropic

from app.labeler import MODEL


def summarize_ticket(client: Anthropic, text: str) -> str:
    """A summary of at most two sentences."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=200,
        system="Summarize the support ticket in at most two sentences for the weekly report.",
        messages=[{"role": "user", "content": text}],
    )
    return "".join(block.text for block in message.content if block.type == "text").strip()
