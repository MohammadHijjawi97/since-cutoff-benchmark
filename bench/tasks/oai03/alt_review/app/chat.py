"""Help-desk chat backend: answers customer questions with the OpenAI API.

Reviewer's alternative answer: the reference, but the warning carries the exception via exc_info (traceback with
the chained network error) instead of naming `__cause__` in the message.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator

import openai
from openai import OpenAI

from app.errors import UpstreamTimeout, UpstreamUnavailable

MODEL = "gpt-5.5"
SYSTEM_PROMPT = "You are the help-desk assistant for Northwind Cloud. Answer briefly and concretely."
ATTEMPTS = 3

logger = logging.getLogger("app.chat")


def build_messages(question: str, history: Iterable[tuple[str, str]] = ()) -> list[dict[str, str]]:
    """System prompt, then earlier (question, answer) turns, then the new question."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for asked, answered in history:
        messages.append({"role": "user", "content": asked})
        messages.append({"role": "assistant", "content": answered})
    messages.append({"role": "user", "content": question})
    return messages


def iter_answer(client: OpenAI, question: str, history: Iterable[tuple[str, str]] = ()) -> Iterator[str]:
    """Yield the answer's text as it streams in (used by the websocket channel)."""
    stream = client.chat.completions.create(
        model=MODEL,
        messages=build_messages(question, history),
        stream=True,
    )
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content


def answer(client: OpenAI, question: str, history: Iterable[tuple[str, str]] = ()) -> str:
    """The complete answer to `question` (used by the e-mail channel).

    openai 3.x raises its own APITimeoutError / APIConnectionError for transport failures while a stream
    is consumed too (not raw HTTP-client exceptions); the network error itself is the `__cause__`.
    """
    history = list(history)
    for attempt in range(1, ATTEMPTS + 1):
        try:
            return "".join(iter_answer(client, question, history))
        except openai.APITimeoutError as exc:
            raise UpstreamTimeout(f"the model provider timed out: {exc.__cause__ or exc}") from exc
        except openai.APIConnectionError as exc:
            logger.warning("answer attempt %d/%d failed", attempt, ATTEMPTS, exc_info=exc)
    raise UpstreamUnavailable(f"no complete answer after {ATTEMPTS} attempts")
