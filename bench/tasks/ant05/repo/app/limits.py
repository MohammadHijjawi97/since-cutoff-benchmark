"""Claude calls that also report the remaining token budget (used by the CLI)."""

from anthropic import Anthropic

MODEL = "claude-sonnet-4-6"
TOKENS_REMAINING = "anthropic-ratelimit-tokens-remaining"
SYSTEM = "Classify the support ticket as billing, bug, account or other, then give a one-line reason."


def ask_with_limits(client: Anthropic, prompt: str) -> dict:
    """The answer plus the rate-limit budget reported with the same response."""
    raw = client.messages.with_raw_response.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    message = raw.parse()
    return {
        "answer": "".join(block.text for block in message.content if block.type == "text"),
        "tokens_remaining": int(raw.headers[TOKENS_REMAINING]),
        "request_id": raw.headers.get("request-id"),
    }
