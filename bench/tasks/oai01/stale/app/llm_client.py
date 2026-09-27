"""Factory for the OpenAI client used by the search bot (2.x-era code)."""

import logging

import httpx
from openai import DefaultHttpxClient, OpenAI

logger = logging.getLogger("app.http")


def _log_request(request: httpx.Request) -> None:
    logger.info("%s %s", request.method, request.url)


def build_client(api_key: str, transport=None) -> OpenAI:
    timeout = httpx.Timeout(30.0, connect=5.0)
    kwargs = {"transport": transport} if transport is not None else {}
    http_client = DefaultHttpxClient(timeout=timeout, event_hooks={"request": [_log_request]}, **kwargs)
    return OpenAI(api_key=api_key, max_retries=2, timeout=timeout, http_client=http_client)
