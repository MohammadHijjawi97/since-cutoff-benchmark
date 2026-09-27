"""Support-ticket labeler."""

from anthropic import Anthropic

LABELS = ("bug", "feature", "question")
MODEL = "claude-sonnet-4-6"


def label_ticket(client: Anthropic, text: str) -> str:
    raise NotImplementedError
