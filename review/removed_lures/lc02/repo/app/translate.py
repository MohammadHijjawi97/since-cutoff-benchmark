"""Translate agent replies before they are sent to the customer."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel

from app.prompts import TRANSLATE_PROMPT


def translate_reply(chat: BaseChatModel, text: str, language: str) -> str:
    """The reply translated into `language` (for example "German")."""
    return chat.predict(TRANSLATE_PROMPT.format(language=language, text=text)).strip()
