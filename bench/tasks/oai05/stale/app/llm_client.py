"""Factory for the OpenAI client used by the search bot (openai 3.x code: too new for this project)."""

import logging

import httpx2
from openai import DefaultHttpx2Client, OpenAI

logger = logging.getLogger("app.http")


def _log_request(request: httpx2.Request) -> None:
    logger.info("%s %s", request.method, request.url)


def build_client(api_key: str, transport=None) -> OpenAI:
    timeout = httpx2.Timeout(30.0, connect=5.0)
    kwargs = {"transport": transport} if transport is not None else {}
    http_client = DefaultHttpx2Client(timeout=timeout, event_hooks={"request": [_log_request]}, **kwargs)
    return OpenAI(api_key=api_key, max_retries=2, timeout=timeout, http_client=http_client)
