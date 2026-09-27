"""Claude access for the assistant (alternative answer: the SDK's HTTP library used directly)."""

import httpx2
from anthropic import Anthropic

from app.http import CONNECT_TIMEOUT, EGRESS_TAG, READ_TIMEOUT, log_egress

MODEL = "claude-opus-5-5"


def build_claude(api_key: str, transport=None) -> Anthropic:
    http_client = httpx2.Client(
        timeout=httpx2.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
        event_hooks={"request": [log_egress]},
        transport=transport,
    )
    return Anthropic(api_key=api_key, max_retries=2, default_headers={"X-Egress-Tag": EGRESS_TAG},
                     http_client=http_client)


def ask(client: Anthropic, question: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You are the on-call assistant. Answer briefly.",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
