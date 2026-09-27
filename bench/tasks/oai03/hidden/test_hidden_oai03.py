"""oai03 hidden tests: answer() retries dropped connections, logs the network reason, and does not retry timeouts.

A scripted provider behind the SDK's own HTTP client (mock transport, no network) streams, drops mid-stream,
stalls mid-stream, refuses the connection or times out before the first byte. Runs at openai 3.19.2 (pinned)
and 2.44.0 (cutoff era).
"""

import json
import logging

import openai
import pytest

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - openai<3
    import httpx as hx

from app.chat import MODEL, answer
from app.errors import UpstreamTimeout, UpstreamUnavailable

DROP = "peer closed connection without sending complete message body (received 118 of 406 bytes)"
SSE = {"content-type": "text/event-stream"}


def chunk(delta, finish_reason=None):
    body = {"id": "chatcmpl-7", "object": "chat.completion.chunk", "created": 1767225600, "model": MODEL,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}]}
    return f"data: {json.dumps(body)}\n\n".encode()


def events(*texts, complete=True):
    parts = [chunk({"role": "assistant", "content": texts[0]})] + [chunk({"content": t}) for t in texts[1:]]
    if complete:
        parts += [chunk({}, "stop"), b"data: [DONE]\n\n"]
    return parts


class Body(hx.SyncByteStream):
    """Response body that yields `parts`, then raises `error` (a connection that dies mid-stream)."""

    def __init__(self, parts, error=None):
        self.parts = parts
        self.error = error

    def __iter__(self):
        yield from self.parts
        if self.error is not None:
            raise self.error


class Provider:
    """Answers attempt n with script[n]: ("ok", texts), ("drop", texts), ("stall", texts), ("refused",), ("slow",)."""

    def __init__(self, *script):
        self.script = list(script)
        self.requests = []

    def __call__(self, request):
        self.requests.append(json.loads(request.content))
        step = self.script.pop(0) if self.script else ("ok", ["unexpected extra attempt"])
        kind = step[0]
        if kind == "ok":
            return hx.Response(200, headers=SSE, stream=Body(events(*step[1])))
        if kind == "drop":
            return hx.Response(200, headers=SSE, stream=Body(events(*step[1], complete=False), hx.RemoteProtocolError(DROP)))
        if kind == "stall":
            return hx.Response(200, headers=SSE, stream=Body(events(*step[1], complete=False), hx.ReadTimeout("The read operation timed out")))
        if kind == "refused":
            raise hx.ConnectError("[Errno 111] Connection refused")
        if kind == "slow":
            raise hx.ReadTimeout("The read operation timed out")
        raise AssertionError(kind)


def client_for(provider):
    http_client = openai.DefaultHttpxClient(transport=hx.MockTransport(provider))
    return openai.OpenAI(api_key="sk-test", max_retries=0, http_client=http_client)


def warnings_text(caplog):
    formatter = logging.Formatter("%(message)s")
    return [formatter.format(r) for r in caplog.records if r.name == "app.chat" and r.levelno == logging.WARNING]


@pytest.fixture(autouse=True)
def capture(caplog):
    caplog.set_level(logging.INFO, logger="app.chat")


def test_complete_stream_is_returned_in_one_request(caplog):
    provider = Provider(("ok", ["Restart the ", "sync agent."]))
    assert answer(client_for(provider), "Files are not syncing") == "Restart the sync agent."
    assert len(provider.requests) == 1
    body = provider.requests[0]
    assert body["model"] == MODEL and body["stream"] is True
    assert body["messages"][-1] == {"role": "user", "content": "Files are not syncing"}
    assert warnings_text(caplog) == []


def test_drop_mid_stream_is_retried_from_scratch_and_logs_the_network_reason(caplog):
    provider = Provider(("drop", ["Restart the "]), ("ok", ["Clear the ", "cache."]))
    assert answer(client_for(provider), "Files are not syncing") == "Clear the cache."
    assert len(provider.requests) == 2
    logged = warnings_text(caplog)
    assert any(DROP in line for line in logged), logged


def test_gives_up_after_three_dropped_attempts(caplog):
    provider = Provider(("drop", ["A"]), ("drop", ["B"]), ("drop", ["C"]), ("ok", ["too late"]))
    with pytest.raises(UpstreamUnavailable):
        answer(client_for(provider), "Is the API down?")
    assert len(provider.requests) == 3
    assert sum(DROP in line for line in warnings_text(caplog)) >= 2


def test_refused_connection_is_retried():
    provider = Provider(("refused",), ("refused",), ("ok", ["Back ", "online."]))
    assert answer(client_for(provider), "Status?") == "Back online."
    assert len(provider.requests) == 3


def test_stall_mid_stream_raises_timeout_without_retry():
    provider = Provider(("stall", ["Partial "]), ("ok", ["must not be requested"]))
    with pytest.raises(UpstreamTimeout):
        answer(client_for(provider), "Long question")
    assert len(provider.requests) == 1


def test_timeout_before_the_first_byte_raises_timeout_without_retry():
    provider = Provider(("slow",), ("ok", ["must not be requested"]))
    with pytest.raises(UpstreamTimeout):
        answer(client_for(provider), "Long question")
    assert len(provider.requests) == 1
