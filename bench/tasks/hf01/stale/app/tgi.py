"""Client for our self-hosted TGI endpoint (pre-2.0 code)."""

from huggingface_hub import InferenceClient


def complete_paragraph(endpoint_url: str, prompt: str) -> str:
    client = InferenceClient(model=endpoint_url)
    text = client.text_generation(prompt, max_new_tokens=200, stop_sequences=["\n\n"])
    return text.rstrip()
