"""Translate agent replies before they are sent to the customer."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.prompts import TRANSLATE_PROMPT


def translate_replies(chat: BaseChatModel, texts: list[str], language: str) -> list[str]:
    """Each reply translated into `language` (for example "German"), in the same order.

    The replies of one conversation are translated together, so the chat model can run the requests
    concurrently.
    """
    prompts = [TRANSLATE_PROMPT.format(language=language, text=text) for text in texts]
    return [str(message.content).strip() for message in chat.batch(prompts)]
