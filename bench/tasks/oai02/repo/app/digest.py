"""Weekly support digest: a headline and a short summary for each customer thread."""

from __future__ import annotations

import os
from functools import lru_cache

from openai import OpenAI

MODEL = "gpt-5.5-mini"

SUMMARY_PROMPT = "Summarise the support thread in at most two sentences. No preamble."
HEADLINE_PROMPT = "Write a headline of at most eight words for the support thread. No quotes."


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    """The process-wide client, created on first use and reused afterwards."""
    return OpenAI(
        api_key=os.environ.get("DIGEST_OPENAI_KEY", "sk-local-dev"),
        max_retries=2,
        timeout=30.0,
    )


def _ask(system: str, thread: str, max_tokens: int) -> str:
    completion = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": thread},
        ],
        max_completion_tokens=max_tokens,
    )
    return (completion.choices[0].message.content or "").strip()


def summarize(thread: str) -> str:
    return _ask(SUMMARY_PROMPT, thread, 200)


def headline(thread: str) -> str:
    return _ask(HEADLINE_PROMPT, thread, 24).rstrip(".")


def build_digest(threads: dict[str, str]) -> list[dict[str, str]]:
    """One row per thread, sorted by thread id."""
    return [
        {"id": thread_id, "headline": headline(text), "summary": summarize(text)}
        for thread_id, text in sorted(threads.items())
    ]
