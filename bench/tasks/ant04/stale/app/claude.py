"""Claude access for the assistant (0.x-era: the project's httpx.Client passed as http_client)."""

from anthropic import Anthropic

from app.http import build_http_client

MODEL = "claude-opus-5-5"


def build_claude(api_key: str, transport=None) -> Anthropic:
    return Anthropic(api_key=api_key, max_retries=2, http_client=build_http_client(transport=transport))


def ask(client: Anthropic, question: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You are the on-call assistant. Answer briefly.",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
