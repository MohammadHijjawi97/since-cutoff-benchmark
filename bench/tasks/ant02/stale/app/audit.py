"""Calls to Claude whose raw HTTP exchange is kept for the audit log (0.x-era code)."""

from anthropic import Anthropic

MODEL = "claude-opus-5-5"


def ask_with_audit(client: Anthropic, prompt: str) -> dict:
    raw = client.messages.with_raw_response.create(
        model=MODEL, max_tokens=256, messages=[{"role": "user", "content": prompt}]
    )
    message = raw.parse()
    return {
        "request_id": raw.headers.get("request-id"),
        "raw_body": raw.text,
        "answer": "".join(b.text for b in message.content if b.type == "text"),
    }
