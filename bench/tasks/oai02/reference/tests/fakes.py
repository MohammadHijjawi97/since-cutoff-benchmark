"""Test doubles for the OpenAI API, shared by the digest tests (and copied into the ops-bot repo)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator
from unittest import mock

import httpx2

OPENAI_HOST = "api.openai.com"
CHAT_COMPLETIONS_PATH = "/v1/chat/completions"


def chat_completion(text: str, model: str = "gpt-5.5-mini") -> dict:
    """A minimal `chat.completion` payload whose only choice says `text`."""
    return {
        "id": "chatcmpl-fake",
        "object": "chat.completion",
        "created": 1767225600,
        "model": model,
        "choices": [
            {
                "index": 0,
                "finish_reason": "stop",
                "logprobs": None,
                "message": {"role": "assistant", "content": text, "refusal": None},
            }
        ],
        "usage": {"prompt_tokens": 12, "completion_tokens": 5, "total_tokens": 17},
    }


@contextmanager
def mock_openai(*replies: str) -> Iterator[list[dict]]:
    """Fake the OpenAI API for the duration of the `with` block.

    Every chat-completions request that a synchronous `openai.OpenAI` client sends while the
    block is active is answered with the next canned reply instead of reaching the network,
    whichever client sends it: app.digest's cached client, clients created before the block
    and clients created inside it. Yields the list of JSON request bodies received, in order.
    Nothing is intercepted once the block has exited. A request beyond the canned replies gets
    a 400 error response.

    openai 3.x sends its requests through httpx2, which respx does not patch, so the fake
    patches httpx2's transport class itself (the same place respx hooked into for httpx).
    """
    seen: list[dict] = []
    pending = list(replies)
    real_handle_request = httpx2.HTTPTransport.handle_request

    def handle_request(transport: httpx2.HTTPTransport, request: httpx2.Request) -> httpx2.Response:
        if request.url.host != OPENAI_HOST:
            return real_handle_request(transport, request)
        if request.method != "POST" or request.url.path != CHAT_COMPLETIONS_PATH:
            error = {"message": f"mock_openai: unexpected {request.method} {request.url.path}"}
            return httpx2.Response(404, json={"error": error})
        body = json.loads(request.read())
        seen.append(body)
        if not pending:
            error = {"message": "mock_openai: no canned reply left", "type": "invalid_request_error"}
            return httpx2.Response(400, json={"error": error})
        return httpx2.Response(200, json=chat_completion(pending.pop(0), body.get("model", "")))

    with mock.patch.object(httpx2.HTTPTransport, "handle_request", handle_request):
        yield seen
