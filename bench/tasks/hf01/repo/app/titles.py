"""Titles for generated paragraphs, from the same self-hosted TGI server."""

from huggingface_hub import InferenceClient


def suggest_title(endpoint_url: str, paragraph: str) -> str:
    """A title of at most six words for `paragraph`."""
    client = InferenceClient(model=endpoint_url)
    prompt = f"Write a title of at most six words for this paragraph.\n\n{paragraph}\n\nTitle:"
    return client.text_generation(prompt, max_new_tokens=16).strip()
