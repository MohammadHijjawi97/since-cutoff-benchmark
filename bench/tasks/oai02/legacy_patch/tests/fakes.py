"""Test doubles for the OpenAI API (cutoff-era rewrite without respx: patches httpx's transport class)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator
from unittest import mock

import httpx

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
    """Same contract as the respx version; intercepts at httpx.HTTPTransport (openai 2.x's transport)."""
    seen: list[dict] = []
    pending = list(replies)
    real_handle_request = httpx.HTTPTransport.handle_request

    def handle_request(transport: httpx.HTTPTransport, request: httpx.Request) -> httpx.Response:
        if request.url.host != OPENAI_HOST:
            return real_handle_request(transport, request)
        if request.method != "POST" or request.url.path != CHAT_COMPLETIONS_PATH:
            error = {"message": f"mock_openai: unexpected {request.method} {request.url.path}"}
            return httpx.Response(404, json={"error": error})
        body = json.loads(request.read())
        seen.append(body)
        if not pending:
            error = {"message": "mock_openai: no canned reply left", "type": "invalid_request_error"}
            return httpx.Response(400, json={"error": error})
        return httpx.Response(200, json=chat_completion(pending.pop(0), body.get("model", "")))

    with mock.patch.object(httpx.HTTPTransport, "handle_request", handle_request):
        yield seen
