"""Plain questions to Claude (no audit trail needed)."""

from anthropic import Anthropic

from app.audit import MODEL


def ask(client: Anthropic, prompt: str) -> str:
    message = client.messages.create(
        model=MODEL, max_tokens=256, messages=[{"role": "user", "content": prompt}]
    )
    return "".join(block.text for block in message.content if block.type == "text")
