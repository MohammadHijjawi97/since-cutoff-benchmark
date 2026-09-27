"""Test doubles for the OpenAI API, shared by the digest tests (and copied into the ops-bot repo)."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

import httpx
import respx

OPENAI_BASE_URL = "https://api.openai.com/v1"


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
    """
    seen: list[dict] = []
    pending = list(replies)

    def answer(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append(body)
        if not pending:
            error = {"message": "mock_openai: no canned reply left", "type": "invalid_request_error"}
            return httpx.Response(400, json={"error": error})
        return httpx.Response(200, json=chat_completion(pending.pop(0), body.get("model", "")))

    with respx.mock(base_url=OPENAI_BASE_URL, assert_all_called=False) as router:
        router.post("/chat/completions").mock(side_effect=answer)
        yield seen
