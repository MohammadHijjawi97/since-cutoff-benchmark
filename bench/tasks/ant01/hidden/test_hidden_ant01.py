import json

import anthropic
import pytest

try:  # anthropic>=1 is built on httpx2; 0.x on httpx (lets the same test run at the cutoff version)
    import httpx2 as hx
except ImportError:  # pragma: no cover
    import httpx as hx

from app.labeler import MODEL, label_ticket


def make_client(reply: str, seen: list) -> anthropic.Anthropic:
    def handler(request):
        seen.append(json.loads(request.content))
        return hx.Response(
            200,
            headers={"request-id": "req_test"},
            json={
                "id": "msg_01", "type": "message", "role": "assistant", "model": MODEL,
                "content": [{"type": "text", "text": reply}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 12, "output_tokens": 1},
            },
        )

    return anthropic.Anthropic(
        api_key="test-key", max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(handler)),
    )


def test_sends_temperature_zero_and_parses_label():
    seen: list = []
    assert label_ticket(make_client(" Bug\n", seen), "App crashes on save") == "bug"
    assert len(seen) == 1
    body = seen[0]
    assert body["model"] == MODEL
    assert body["max_tokens"] == 5
    assert body.get("temperature") == 0
    assert "App crashes on save" in json.dumps(body["messages"])
    assert body.get("system")


def test_unknown_reply_falls_back_to_question():
    assert label_ticket(make_client("maybe?", []), "hello") == "question"
