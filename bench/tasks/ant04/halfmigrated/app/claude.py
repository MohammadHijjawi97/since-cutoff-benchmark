"""Claude access for the assistant (half-migrated: the SDK's client class, but app/http.py's httpx.Timeout)."""

import anthropic
from anthropic import Anthropic

from app.http import EGRESS_TAG, TIMEOUT, log_egress

MODEL = "claude-opus-5-5"


def build_claude(api_key: str, transport=None) -> Anthropic:
    options = {"transport": transport} if transport is not None else {}
    http_client = anthropic.DefaultHttpxClient(
        timeout=TIMEOUT,
        headers={"X-Egress-Tag": EGRESS_TAG},
        event_hooks={"request": [log_egress]},
        **options,
    )
    return Anthropic(api_key=api_key, max_retries=2, http_client=http_client)


def ask(client: Anthropic, question: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You are the on-call assistant. Answer briefly.",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
