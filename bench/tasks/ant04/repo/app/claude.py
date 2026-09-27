"""Claude access for the assistant."""

from anthropic import Anthropic

MODEL = "claude-opus-5-5"


def build_claude(api_key: str, transport=None) -> Anthropic:
    raise NotImplementedError


def ask(client: Anthropic, question: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You are the on-call assistant. Answer briefly.",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
