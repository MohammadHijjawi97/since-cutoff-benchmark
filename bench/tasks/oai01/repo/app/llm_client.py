"""Factory for the OpenAI client used by the search bot."""

import logging

from openai import OpenAI

logger = logging.getLogger("app.http")


def build_client(api_key: str, transport=None) -> OpenAI:
    raise NotImplementedError
