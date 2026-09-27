"""oai05 hidden tests (pinned-behind): oai01's tests, for a project pinned to openai 2.44.0.

Same assertions as oai01. They run at 2.44.0 (pinned; httpx) and at 3.19.2 (where the too-new httpx2 answer
in stale/ passes).
"""

import logging

try:
    import httpx2 as hx  # openai>=3 (gate 4 only)
except ImportError:  # openai<3: the pinned version of this project
    import httpx as hx

from app.llm_client import build_client

MODELS = {"object": "list", "data": [{"id": "gpt-5.5", "object": "model", "created": 0, "owned_by": "openai"}]}


def test_logs_each_request_and_uses_transport(caplog):
    calls = []

    def handler(request):
        calls.append(request)
        return hx.Response(200, json=MODELS)

    caplog.set_level(logging.INFO, logger="app.http")
    client = build_client("sk-test", transport=hx.MockTransport(handler))
    assert [m.id for m in client.models.list().data] == ["gpt-5.5"]
    assert len(calls) == 1
    lines = [r.getMessage() for r in caplog.records if r.name == "app.http"]
    assert any(line.startswith("GET ") and line.endswith("/v1/models") for line in lines), lines


def test_retries_are_logged_too(caplog):
    attempts = []

    def flaky(request):
        attempts.append(1)
        if len(attempts) == 1:
            return hx.Response(500, json={"error": {"message": "boom"}})
        return hx.Response(200, json=MODELS)

    caplog.set_level(logging.INFO, logger="app.http")
    client = build_client("sk-test", transport=hx.MockTransport(flaky))
    client.models.list()
    assert len(attempts) == 2
    assert len([r for r in caplog.records if r.name == "app.http"]) >= 2


def test_timeouts_and_retries():
    client = build_client("sk-test", transport=hx.MockTransport(lambda r: hx.Response(200, json=MODELS)))
    t = client.timeout
    assert (t.connect, t.read, t.write, t.pool) == (5, 30, 30, 30)
    assert client.max_retries == 2
