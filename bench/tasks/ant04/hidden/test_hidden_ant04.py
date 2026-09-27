"""ant04: a custom HTTP client for the Anthropic SDK (anthropic 1.8.0; stale form passes at 0.115.0).

Offline: build_claude() gets a MockTransport of the HTTP library the installed SDK is built on. Checks
the behaviour the instruction asks for: the egress header, one log line per request (retries included),
the timeouts that reach the transport, max_retries, and that requests go through the given transport.
"""

import json
import logging

import anthropic

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - anthropic<1
    import httpx as hx

from app.claude import MODEL, ask, build_claude
from app.http import EGRESS_TAG

MESSAGE = {
    "id": "msg_04", "type": "message", "role": "assistant", "model": MODEL,
    "content": [{"type": "text", "text": "All systems operational."}],
    "stop_reason": "end_turn", "stop_sequence": None,
    "usage": {"input_tokens": 21, "output_tokens": 5},
}
OVERLOADED = {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}


def egress_lines(caplog) -> list[str]:
    return [r.getMessage() for r in caplog.records if r.name == "app.egress"]


def test_claude_requests_follow_the_egress_rules(caplog):
    seen = []

    def handler(request):
        seen.append(request)
        return hx.Response(200, headers={"request-id": "req_ant04"}, json=MESSAGE)

    caplog.set_level(logging.INFO, logger="app.egress")
    client = build_claude("sk-ant-test", transport=hx.MockTransport(handler))

    assert isinstance(client, anthropic.Anthropic)
    assert client.max_retries == 2
    assert ask(client, "Is the API up?") == "All systems operational."

    assert len(seen) == 1, "requests must go through the given transport"
    request = seen[0]
    assert request.headers.get("x-egress-tag") == EGRESS_TAG
    assert request.headers.get("x-api-key") == "sk-ant-test"
    assert json.loads(request.content)["model"] == MODEL
    timeout = request.extensions.get("timeout") or {}
    assert timeout.get("connect") == 5.0, timeout
    assert timeout.get("read") == 60.0, timeout
    assert egress_lines(caplog) == ["POST https://api.anthropic.com/v1/messages"]


def test_retries_are_logged_too(caplog):
    attempts = []

    def flaky(request):
        attempts.append(request)
        if len(attempts) == 1:
            return hx.Response(529, headers={"retry-after-ms": "5"}, json=OVERLOADED)
        return hx.Response(200, json=MESSAGE)

    caplog.set_level(logging.INFO, logger="app.egress")
    client = build_claude("sk-ant-test", transport=hx.MockTransport(flaky))

    assert ask(client, "Is the API up?") == "All systems operational."
    assert len(attempts) == 2
    assert all(a.headers.get("x-egress-tag") == EGRESS_TAG for a in attempts)
    assert egress_lines(caplog) == ["POST https://api.anthropic.com/v1/messages"] * 2
