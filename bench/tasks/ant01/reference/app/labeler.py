"""Support-ticket labeler."""

from anthropic import Anthropic

LABELS = ("bug", "feature", "question")
MODEL = "claude-sonnet-4-6"


def label_ticket(client: Anthropic, text: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=5,
        system="Classify the support ticket. Answer with exactly one word: bug, feature or question.",
        messages=[{"role": "user", "content": text}],
        # anthropic>=1 removed temperature/top_p/top_k from the signature; older models still honour them via extra_body
        extra_body={"temperature": 0},
    )
    reply = "".join(block.text for block in message.content if block.type == "text").strip().lower()
    return reply if reply in LABELS else "question"
