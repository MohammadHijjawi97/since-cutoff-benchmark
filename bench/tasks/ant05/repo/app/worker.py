"""Async triage worker: classifies queued tickets and backs off when the token budget runs low."""

from anthropic import AsyncAnthropic

from app.limits import MODEL, SYSTEM, TOKENS_REMAINING

LOW_WATERMARK = 2_000  # tokens; below this the worker pauses its queue


async def triage(client: AsyncAnthropic, ticket: str) -> dict:
    raise NotImplementedError
