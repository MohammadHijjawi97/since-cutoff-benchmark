"""ant05: async raw responses (anthropic 1.8.0; stale form passes at 0.115.0).

Offline: an AsyncAnthropic client on a MockTransport; the coroutine is driven with asyncio.run so no
pytest plugin is needed. Checks the returned values (answer, budget header, request id, throttle flag)
and that exactly one request was sent.
"""

import asyncio
import json

import anthropic

try:
    import httpx2 as hx
except ImportError:  # pragma: no cover - anthropic<1
    import httpx as hx

from app.limits import MODEL
from app.worker import LOW_WATERMARK, triage


def make_client(remaining: int, seen: list) -> anthropic.AsyncAnthropic:
    def handler(request):
        seen.append(json.loads(request.content))
        return hx.Response(
            200,
            headers={"request-id": "req_w17", "anthropic-ratelimit-tokens-remaining": str(remaining)},
            json={
                "id": "msg_05", "type": "message", "role": "assistant", "model": MODEL,
                "content": [{"type": "text", "text": "billing: "}, {"type": "text", "text": "charged twice"}],
                "stop_reason": "end_turn", "stop_sequence": None,
                "usage": {"input_tokens": 40, "output_tokens": 6},
            },
        )

    return anthropic.AsyncAnthropic(
        api_key="test-key", max_retries=0,
        http_client=anthropic.DefaultAsyncHttpxClient(transport=hx.MockTransport(handler)),
    )


def test_returns_answer_budget_and_request_id():
    seen: list = []
    result = asyncio.run(triage(make_client(48_000, seen), "I was charged twice for September"))
    assert result == {"answer": "billing: charged twice", "tokens_remaining": 48_000,
                      "request_id": "req_w17", "throttle": False}
    assert len(seen) == 1, "one request per ticket"
    assert seen[0]["model"] == MODEL and seen[0]["max_tokens"] == 512
    assert "charged twice for September" in json.dumps(seen[0]["messages"])
    json.dumps(result)  # the worker publishes the dict on its status channel


def test_low_budget_asks_the_worker_to_throttle():
    result = asyncio.run(triage(make_client(LOW_WATERMARK - 1, []), "Password reset mail never arrives"))
    assert result["throttle"] is True
    assert result["tokens_remaining"] == LOW_WATERMARK - 1
    assert result["answer"] == "billing: charged twice"
