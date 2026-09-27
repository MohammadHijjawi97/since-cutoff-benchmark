"""Async triage worker (alternative answer: the streaming-response context manager)."""

from anthropic import AsyncAnthropic

from app.limits import MODEL, SYSTEM, TOKENS_REMAINING

LOW_WATERMARK = 2_000  # tokens; below this the worker pauses its queue


async def triage(client: AsyncAnthropic, ticket: str) -> dict:
    async with client.messages.with_streaming_response.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM,
        messages=[{"role": "user", "content": ticket}],
    ) as response:
        message = await response.parse()
        remaining = int(response.headers[TOKENS_REMAINING])
        request_id = response.headers.get("request-id")
    return {
        "answer": "".join(block.text for block in message.content if block.type == "text"),
        "tokens_remaining": remaining,
        "request_id": request_id,
        "throttle": remaining < LOW_WATERMARK,
    }
