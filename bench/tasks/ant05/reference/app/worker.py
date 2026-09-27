"""Async triage worker: classifies queued tickets and backs off when the token budget runs low."""

from anthropic import AsyncAnthropic

from app.limits import MODEL, SYSTEM, TOKENS_REMAINING

LOW_WATERMARK = 2_000  # tokens; below this the worker pauses its queue


async def triage(client: AsyncAnthropic, ticket: str) -> dict:
    raw = await client.messages.with_raw_response.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM,
        messages=[{"role": "user", "content": ticket}],
    )
    # anthropic>=1: the async raw response's parse() is a coroutine (it was a plain method on the 0.x legacy class)
    message = await raw.parse()
    remaining = int(raw.headers[TOKENS_REMAINING])
    return {
        "answer": "".join(block.text for block in message.content if block.type == "text"),
        "tokens_remaining": remaining,
        "request_id": raw.headers.get("request-id"),
        "throttle": remaining < LOW_WATERMARK,
    }
