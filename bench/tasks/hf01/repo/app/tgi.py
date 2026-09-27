"""Client for our self-hosted TGI endpoint."""

from huggingface_hub import InferenceClient


def complete_paragraph(endpoint_url: str, prompt: str) -> str:
    raise NotImplementedError
