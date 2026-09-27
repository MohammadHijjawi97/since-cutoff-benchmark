"""Claude access for the assistant.

Reviewer's alternative answer: timeout and egress header on the SDK client (timeout=, default_headers=), hook and
transport on the SDK's HTTP client class.
"""
import anthropic
from anthropic import Anthropic

from app.http import CONNECT_TIMEOUT, EGRESS_TAG, READ_TIMEOUT, log_egress

MODEL = "claude-opus-5-5"


def build_claude(api_key: str, transport=None) -> Anthropic:
    kwargs = {"transport": transport} if transport is not None else {}
    return Anthropic(
        api_key=api_key,
        max_retries=2,
        timeout=anthropic.Timeout(READ_TIMEOUT, connect=CONNECT_TIMEOUT),
        default_headers={"X-Egress-Tag": EGRESS_TAG},
        http_client=anthropic.DefaultHttpxClient(event_hooks={"request": [log_egress]}, **kwargs),
    )


def ask(client: Anthropic, question: str) -> str:
    message = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="You are the on-call assistant. Answer briefly.",
        messages=[{"role": "user", "content": question}],
    )
    return "".join(block.text for block in message.content if block.type == "text")
