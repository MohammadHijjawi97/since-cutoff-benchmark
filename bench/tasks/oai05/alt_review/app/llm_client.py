"""Factory for the OpenAI client used by the search bot.

Reviewer's alternative answer: a plain httpx.Client, the timeout only on the HTTP client, the hook defined inline.
"""
import logging

import httpx
from openai import OpenAI

logger = logging.getLogger("app.http")


def build_client(api_key: str, transport=None) -> OpenAI:
    def log_request(request):
        logger.info("%s %s", request.method, request.url)

    http_client = httpx.Client(
        timeout=httpx.Timeout(connect=5.0, read=30.0, write=30.0, pool=30.0),
        event_hooks={"request": [log_request]},
        transport=transport,
    )
    return OpenAI(api_key=api_key, max_retries=2, http_client=http_client)
