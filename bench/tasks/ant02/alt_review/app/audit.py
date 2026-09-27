"""Calls to Claude whose raw HTTP exchange is kept for the audit log.

Reviewer's alternative answer: the body taken from the underlying HTTP response object
(`raw.http_response.text`) instead of the SDK response's own text accessor.
"""

from anthropic import Anthropic

MODEL = "claude-opus-5-5"


def ask_with_audit(client: Anthropic, prompt: str) -> dict:
    raw = client.messages.with_raw_response.create(
        model=MODEL, max_tokens=256, messages=[{"role": "user", "content": prompt}]
    )
    message = raw.parse()
    return {
        "request_id": raw.headers.get("request-id"),
        "raw_body": raw.http_response.text,
        "answer": "".join(b.text for b in message.content if b.type == "text"),
    }
