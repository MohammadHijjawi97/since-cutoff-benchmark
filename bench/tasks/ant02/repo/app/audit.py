"""Calls to Claude whose raw HTTP exchange is kept for the audit log."""

from anthropic import Anthropic

MODEL = "claude-opus-5-5"


def ask_with_audit(client: Anthropic, prompt: str) -> dict:
    raise NotImplementedError
