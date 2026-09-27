import json

import anthropic

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - anthropic<1
    import httpx as hx

from app.audit import MODEL, ask_with_audit

BODY = {
    "id": "msg_02", "type": "message", "role": "assistant", "model": MODEL,
    "content": [{"type": "text", "text": "Hi "}, {"type": "text", "text": "there"}],
    "stop_reason": "end_turn", "stop_sequence": None,
    "usage": {"input_tokens": 3, "output_tokens": 2},
}


def make_client(seen: list) -> anthropic.Anthropic:
    def handler(request):
        seen.append(json.loads(request.content))
        return hx.Response(200, headers={"request-id": "req_123"}, content=json.dumps(BODY).encode())

    return anthropic.Anthropic(
        api_key="test-key", max_retries=0,
        http_client=anthropic.DefaultHttpxClient(transport=hx.MockTransport(handler)),
    )


def test_returns_request_id_raw_body_and_answer():
    seen: list = []
    result = ask_with_audit(make_client(seen), "Say hi")
    assert result["request_id"] == "req_123"
    assert isinstance(result["raw_body"], str)
    assert json.loads(result["raw_body"]) == BODY
    assert result["answer"] == "Hi there"
    assert seen[0]["max_tokens"] == 256 and seen[0]["model"] == MODEL
    json.dumps(result)  # the audit log serialises the dict
